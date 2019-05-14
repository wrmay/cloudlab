import json
import logging
import os
import os.path
import pkg_resources
import shutil
import stat
import subprocess
import sys
import time
import yaml

COMMANDS = ['mkenv', 'rmenv', 'help']
config = None  # config is global


def print_help():
    print('Make a new environment:               cloudlab mkenv path/envname')
    print('Destroy an existing environment:      cloudlab rmenv path/envname ')
    print()
    print('A file named "cloudlab_config.yaml" must be present in the current directory.')
    print('See the sample below.')
    print()
    print('---')
    print('   region: us-east-2')
    print('   instance_count: 3')
    print('   instance_type: m4.medium')


def run():
    global config

    if len(sys.argv) < 3:
        print_help()
        sys.exit(1)

    command = sys.argv[1]
    if command not in COMMANDS:
        sys.exit('Unrecognized command: {0}'.format(command))

    if not os.path.isfile('cloudlab_config.yaml'):
        sys.exit('Exiting because the configuration file is not present. Run "cloudlab help" for details.')

    with open('cloudlab_config.yaml', 'r') as config_file:
        config = yaml.safe_load(config_file)

    envdir = sys.argv[2]

    logging.basicConfig(format='%(asctime)s:%(message)s', level=logging.DEBUG)

    if command == COMMANDS[0]:
        mkenv(envdir)
    elif command == COMMANDS[-1]:
        print_help()
        sys.exit(0)
    else:
        rmenv(envdir)


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


def mkenv(envdir):
    global config

    # create the directory
    if envdir.endswith('/'):
        envdir = envdir[0:-1]

    envname = os.path.basename(envdir)

    if os.path.exists(envdir):
        sys.exit('Environment directory already exists. Exiting.')

    os.makedirs(envdir)
    logging.info('Created directory %s', envdir)

    # generate the yaml file and save it to the target environment
    config['key_pair_name'] = envname
    with open(os.path.join(envdir, 'tplate.yaml'), 'w') as tplate_config_file:
        yaml.dump(config, tplate_config_file)

    logging.info('Wrote "tplate.yaml" file to %s.', envdir)

    sourcedir = pkg_resources.resource_filename('cloudlab', 'plans/aws_basic')

    result = subprocess.run(['tplate', sourcedir, envdir], check=False, stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT)
    if result.returncode != 0:
        sys.exit('Template generation failed with the following output: {}'.format(result.stdout))

    logging.info('Generated aws cloud formation template to %s.', envdir)

    # create the key pair
    result = runaws('aws ec2 create-key-pair --key-name={}'.format(envname))

    keyfile_name = os.path.join(envdir, envname + '.pem')
    with open(keyfile_name, 'w') as f:
        f.write(result['KeyMaterial'])

    os.chmod(keyfile_name, stat.S_IRUSR | stat.S_IWUSR)

    logging.info('Created a new key pair and saved the private key to {}.'.format(keyfile_name))

    # deploy to AWS using Cloud Formation
    runaws('aws cloudformation create-stack --stack-name={} --template-body=file://{}'
           .format(envname, os.path.join(envdir, 'aws-cloud-template.yaml')))

    logging.info('Cloud Formation stack created.  Waiting for provisioning to complete.')

    # now we will use aws cloudformation describe-stack-events to follow the progress
    done = False
    previously_seen = dict()
    while not done:
        time.sleep(5.0)
        result = runaws('aws cloudformation describe-stack-events --stack-name={}'.format(envname))
        for event in reversed(result['StackEvents']):
            if event['EventId'] in previously_seen:
                continue
            else:
                if not event['ResourceStatus'].endswith('IN_PROGRESS'):
                    logging.info('Provisioning event: %s %s',
                        event['LogicalResourceId'] if event['ResourceType'] != 'AWS::CloudFormation::Stack' else 'CloudLab {}'.format(envname),
                        event['ResourceStatus'])

                previously_seen[event['EventId']] = event
                if event['ResourceType'] == 'AWS::CloudFormation::Stack' and event['ResourceStatus'] != 'CREATE_IN_PROGRESS':
                    done = True

    result = runaws('aws cloudformation describe-stacks --stack-name={}'.format(envname))
    status = result['Stacks'][0]['StackStatus']
    if status != 'CREATE_COMPLETE':
        sys.exit('There was a failure while creating the CloudFormation stack.')
    else:
        logging.info('Cloud formation stack created.')

    # now use the outputs section of the describe-stacks result to write an Ansible inventory file.
    invfile = os.path.join(envdir, 'cloudlab_{}.ini'.format(envname))
    with open(invfile, 'w') as f:
        for i in range(1, config['instance_count'] + 1):
            public_ip = ''
            private_ip = ''
            for output in result['Stacks'][0]['Outputs']:
                if output['OutputKey'] == 'Instance{}PublicIpAddress'.format(i):
                    public_ip = output['OutputValue']
                elif output['OutputKey'] == 'Instance{}PrivateIpAddress'.format(i):
                    private_ip = output['OutputValue']

                if len(public_ip) > 0 and len(private_ip) > 0:
                    break

            f.write('{}  private_ip={}\n'.format(public_ip, private_ip))

    logging.info('Wrote inventory to {}'.format(invfile))


# automatically appends --region= --output=json
def runaws(commands):
    cmdarray = commands.split()
    cmdarray += ['--region={}'.format(config['region']), '--output=json']

    result = subprocess.run(cmdarray, check=False, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)

    if result.returncode != 0:
        sys.exit('Exiting because an error occurred while running: {}.  The output was: {}'.format(' '.join(cmdarray),
                                                                                                   result.stdout))
    if len(result.stdout) > 0:
        return json.loads(result.stdout)
    else:
        return None
