# Cloudlab Overview

Cloudlab allows you to quickly provision a lab environment on AWS.  It attempts to strike a good balance between
configurability and ease of use.

Cloudlab provisions a single VPC on AWS with a /16 address space.  Within the VPC, 1 or more subnets can be configured.  
All subnets are public and all have their own /24 address space inside the VPC.  

Notes:
- All instances (hosts) will have an Amazon assigned public IP address and DNS name.
- All hosts can initiate connections to any server either in or outside of the private network
- All hosts accept inbound connections on port 22
- Other than port 22, hosts will only accept inbound connections on specific ports which can be configured per host
- Each environment provisioned with cloudlab will have its own ssh key which will be shared by all the hosts.


After provisioning is complete, Cloudlab will write an Ansible inventory file which can be used for further provisioning.
Cloudlab supports the idea of roles, which will be propagated to the Ansible inventory file.

# Setup

Cloudlab requires python 3.  It can be installed using pip.

```
pip install cloudlab
```

Cloudlab requires the aws cli to be present.  See https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html 
for installation instructions.

Next you will need to configure the aws cli with your AWS access key and  secret access key so that it can access your 
account.  Cloudlab uses the the aws cli and will have whatever privileges your cli has.  You can either configure it 
with your root credentials or create a new IAM user and provide  those credentials.  If you create a new IAM user, it 
will need the following permissions.

```json
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Action": [
                "ec2:*",
                "cloudformation:*",
                "elasticloudbalancing:*"
            ],
            "Effect": "Allow",
            "Resource": "*"
        }
    ]
}
```

If your aws cli is not already configured, provide your credentials using the command below.  They will be stored 
under the ".aws" folder in your home directory.  Note that you will be prompted to provide a region but this is
only a default.  You can use cloudlab to deploy into any region.

```
aws configure  # follow the prompts ...
```
# Usage

Create a file called "cloudlab_config.yaml" in the current directory and edit it to describe the environment(s) you
would like to provision.  An example is given below.

```yaml
region: us-east-2
cidr: 10.0.0.0/16  # must be a /16 subnet, must be a non-routable IP (e.g. 10.*.*.*, 192.168.*.*)
roles:
  ClusterMember:   # role names are copied directly into the CloudFormation template and should not contain special characters
    instance_type: m5.xlarge
    ami_name: ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-20240927
    ssh_user: ubuntu
    open_ports: [5701, 5702]
  LoadGenerator:
    instance_type: m5.xlarge
    ami_name: al2023-ami-2023.6.20241111.0-kernel-6.1-x86_64  # will look up the correct one for this region
    ssh_user: ec2-user
    open_ports: [8080]
subnets:
  - az: a                  # will be appended to region, e.g. us-east-2a
    cidr: 10.0.1.0/24      # must be a /24
    servers:
      - private_ip_suffixes: [101, 102]   # only need to give the last octet, becomes 10.0.1.101
        role: ClusterMember
  - az: b
    cidr: 10.0.2.0/24
    servers:
      - private_ip_suffixes: [101, 102]   # creates 2 servers, 10.0.2.101 and 10.0.2.102
        role: ClusterMember
      - private_ip_suffixes: [201]
        role: LoadGenerator
```

Create an environment ...

```
cloudlab mkenv envdir
```

"envdir" should be an absolute or relative path.  The `basename(envdir)` will be used as the name of the environment
and must be unique.

The "envdir" directory will be created.  The process will fail if the directory already exists.

An Ansible inventory file containing both the public and private ip addresses will be written into
"envdir" to facilitate managing the environment with  Ansible playbooks

```
cloudlab rmenv envdir
```

Will destroy a previously created environment.

```
cloudlab update envdir

```

Will cause the environment to be updated based on changes to "cloudlab_config.yaml"

# Release Notes

## v1.2.0 is a major update
- default plan now includes multiple subnets
- configuration formation has changed

## v1.1.9

- updated required verision of PyYAML to >= 5.4 to avoid known vulnerability in earlier versions.

## v1.1.8

- tplate updates broke cloudlab. The tplate version is now pinned to 1.0.3.

## v1.1.7

- Due to a limitation of 60 outputs in an AWS CloudFormation template, it was
  not possible to provision more than 20 servers using cloudlab.  With this
  update, the limit has been raised to 60 servers.

## v1.1.6

- fix for failing "update" command

## v1.1.5

- fixed a bug that caused mkenv to fail

## v1.1.4

- added the "update" command
