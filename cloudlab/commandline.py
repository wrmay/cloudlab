import argparse
import importlib.resources
import json
import logging
import os
import os.path
import re
import shutil
import stat
import subprocess
import sys
import time

import jinja2
import yaml

CLOUDFORMATION_TEMPLATE_NAME = 'cf.yaml'
CONFIG_FILE_NAME = 'cloudlab_config.yaml'
config = None  # config is global


def print_sample():
    sample = importlib.resources.files('cloudlab').joinpath('resources/cloudlab_config.yaml').read_text()
    print(sample)


def run():
    global config

    parser = argparse.ArgumentParser(prog='cloudlab', description='Declarative lab environment builder for AWS')
    parser.add_argument("command", choices=['mkenv', 'rmenv', 'update', 'sample'])
    parser.add_argument("environment", nargs="?", default="cloudlab", help='A unique name for the environment')
    parser.add_argument("--plan", default='aws_with_subnets', help='The name of the template to use when creating this environment')
    parser.add_argument("--no-provision", dest='provision', action='store_false', help='Generate the CloudFormation template but do not provision the environment')

    args = parser.parse_args()

    if args.command == 'sample':
        print_sample()
        sys.exit(0)

    if not os.path.isfile(CONFIG_FILE_NAME):
        sys.exit(f'Exiting because the configuration file is not present. For a starter configuration file, run  "cloudlab sample > {CONFIG_FILE_NAME}"')

    with open(CONFIG_FILE_NAME, 'r') as config_file:
        config = yaml.safe_load(config_file)

    envdir = args.environment
    command = args.command
    template = f'{args.plan}.yaml.j2'
    provision = args.provision

    logging.basicConfig(format='%(asctime)s:%(message)s', level=logging.DEBUG)

    if command == 'mkenv':
        mkenv(envdir, False, template, provision)
    elif command == 'rmenv':
        rmenv(envdir)
    elif command == 'update':
        mkenv(envdir, True, template, provision)


def rmenv(envdir):
    if envdir.endswith('/'):
        envdir = envdir[0:-1]

    envname = os.path.basename(envdir)

    runaws('aws cloudformation delete-stack --stack-name={}'.format(envname))
    logging.info("Deleted cloud formation stack: %s", envname)

    runaws('aws ec2 delete-key-pair --key-name={}'.format(envname))
    logging.info('Deleted the AWS key pair named %s.', envname + '.pem')

    shutil.rmtree(envdir, ignore_errors=True)
    logging.info('Removed cloudlab environment: %s.', envdir)


def mkenv(envdir, update, template, provision):
    global config

    # retrieve the template file
    j2loader = jinja2.PackageLoader('cloudlab', 'plans')
    j2env = jinja2.Environment(loader=j2loader, lstrip_blocks=True, trim_blocks=True)
    try:
        j2_template = j2env.get_template(template)
    except jinja2.exceptions.TemplateNotFound:
        sys.exit(f'cloudlab template not found: {template}')

    # augment the configuration by looking up ami_ids for this region
    for role in config['roles'].values():
        if 'ami_name' in role:
            role['ami_id'] = get_ami_id(role['ami_name'])

    # convert private_ip_suffixes to private_ip_addresses for each server
    for subnet in config['subnets']:
        for group in subnet['servers']:
            private_ip_addresses = []
            for suffix in group['private_ip_suffixes']:
                private_ip_addresses.append( make_ip(subnet['cidr'], suffix))

            group['private_ip_addresses'] = private_ip_addresses

    # create the directory
    if envdir.endswith('/'):
        envdir = envdir[0:-1]

    envname = os.path.basename(envdir)

    if update:
        if not os.path.exists(envdir):
            sys.exit('Environment directory does not exist. Exiting.')
        # else:
        #     shutil.rmtree(envdir, ignore_errors=True)
        #     logging.info('Removed cloudlab environment directory: %s.', envdir)

    else:
        if os.path.exists(envdir):
            sys.exit('Environment directory already exists. Exiting.')

        os.makedirs(envdir)
        logging.info('Created directory %s', envdir)

    # generate the yaml file and save it to the target environment
    config['key_pair_name'] = envname

    # render the template
    cf_template_file = os.path.join(envdir, CLOUDFORMATION_TEMPLATE_NAME)
    with open(cf_template_file, 'w') as f:
        j2_template.stream(config=config).dump(f)

    logging.info(f'Generated Cloud Formation Template: {cf_template_file}')
    if not provision:
        return

    # create the key pair
    keyfile_name = os.path.join(envdir, envname + '.pem')
    if not update:
        result = runaws('aws ec2 create-key-pair --key-name={}'.format(envname))

        with open(keyfile_name, 'w') as f:
            f.write(result['KeyMaterial'])

        os.chmod(keyfile_name, stat.S_IRUSR | stat.S_IWUSR)

        logging.info('Created a new key pair and saved the private key to {}.'.format(keyfile_name))

    # deploy to AWS using Cloud Formation
    nowait = False
    if update:
        # first we need to figure out the latest event related to this stack so we can start watching events after that
        result = runaws(f'aws cloudformation describe-stack-events --stack-name={envname}')
        last_event_timestamp = result['StackEvents'][0]['Timestamp']

        result = runaws_result('aws cloudformation update-stack '
                               f'--stack-name={envname} '
                               f'--template-body=file://{cf_template_file}')

        if result.returncode != 0:
            if 'No updates are to be performed'  in str(result.stdout):
                nowait = True
                logging.info("The Cloudformation stack is already up to date")
            else:
                sys.exit(f'An error occurred while updating the Cloudformation stack: {result.stdout}')

        else:
            logging.info('Waiting for stack update to complete.')
    else:
        runaws('aws cloudformation create-stack '
               f'--stack-name={envname} '
               f'--template-body=file://{cf_template_file}')

        logging.info('Cloud Formation stack created.  Waiting for provisioning to complete.')

    # use aws cloudformation describe-stack-events to follow the progress
    done = nowait
    previously_seen = dict()
    while not done:
        time.sleep(5.0)
        result = runaws(f'aws cloudformation describe-stack-events --stack-name={envname}')
        for event in reversed(result['StackEvents']):
            if update and event['Timestamp'] <= last_event_timestamp:
                continue

            if event['EventId'] in previously_seen:
                continue
            else:
                if not event['ResourceStatus'].endswith('IN_PROGRESS'):
                    logging.info('Provisioning event: %s %s',
                                 event['LogicalResourceId'] if event['ResourceType'] != 'AWS::CloudFormation::Stack' else f'CloudLab {envname}',
                                 event['ResourceStatus'])

                previously_seen[event['EventId']] = event
                if event['ResourceType'] == 'AWS::CloudFormation::Stack' and event['ResourceStatus'].find('COMPLETE') >= 0:
                    done = True

    result = runaws(f'aws cloudformation describe-stacks --stack-name={envname}')
    status = result['Stacks'][0]['StackStatus']

    if update:
        if not status.startswith('UPDATE_COMPLETE'):
            sys.exit('There was a failure while updating the CloudFormation stack.')
        else:
            logging.info('Cloud formation stack updated.')

    else:
        if status != 'CREATE_COMPLETE':
            sys.exit('There was a failure while creating the CloudFormation stack.')
        else:
            logging.info('Cloud formation stack created.')

    # build the inventory
    inventory = {'ansible_ssh_private_key_file': keyfile_name }
    for subnet in config['subnets']:
        for group in subnet['servers']:
            role = group['role']
            for ip_suffix in group['private_ip_suffixes']:
                server_lookup_key = f"Instance{subnet['az'].upper()}{ip_suffix}Attributes"
                attributes = get_cf_output(result, server_lookup_key).split('|')
                public_ip = attributes[0]
                private_ip = attributes[1]
                # dns_name = attributes[2]

                inv_role = inventory.setdefault(role, {'hosts': {}})
                inv_role['hosts'][public_ip] = {
                    'private_ip': private_ip,
                    'ansible_user': config['roles'][role]['ssh_user']
                }

    invfile = os.path.join(envdir, 'inventory.yaml')
    with open(invfile, 'w') as f:
        yaml.dump(inventory, f)

    logging.info('Wrote inventory to {}'.format(invfile))

# returns public_ip, private_ip
def get_cf_output(cf_cmd_result, key):
    result = None
    for output in cf_cmd_result['Stacks'][0]['Outputs']:
        if output['OutputKey'] == key:
            result = output['OutputValue']
            break

    return result

def get_ami_id(ami_name):
    cmd = f'aws ec2 describe-images --query Images[*].[ImageId] --filters Name=name,Values={ami_name}'
    result = runaws(cmd)
    return result[0][0]

# automatically appends --region= --output=json
def runaws(commands):
    cmdarray = commands.split()
    cmdarray += ['--region={}'.format(config['region']), '--output=json']

    result = subprocess.run(cmdarray, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    if result.returncode != 0:
        sys.exit(
            'Exiting because an error occurred while running: {}.  The output was: {}'.format(' '.join(cmdarray),
                                                                                              result.stdout))
    if len(result.stdout) > 0:
        return json.loads(result.stdout)
    else:
        return None

# automatically appends --region= --output=json
def runaws_result(commands):
    cmdarray = commands.split()
    cmdarray += ['--region={}'.format(config['region']), '--output=json']

    return subprocess.run(cmdarray, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

# Parses cidr, extracts the first 3 octets, and appends suffix to then yielding a 4 octet IP
def make_ip(cidr, suffix):
    cidr_re = r'(\d{1,3}\.\d{1,3}\.\d{1,3})\.\d{1,3}/\d{2}'
    suffix_re = r'\d{1,3}'
    match = re.fullmatch(cidr_re, cidr)
    if match is None:
        raise SyntaxError(f'cidr "{cidr}" does not have the expected format.')

    suffix = str(suffix)
    if re.fullmatch(suffix_re, suffix) is None:
        raise SyntaxError(f'suffix "{suffix}" does not have the expected format.')

    return f'{match.group(1)}.{suffix}'
