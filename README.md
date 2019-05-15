# Cloudlab Overview

Cloudlab allows you to quickly provision a lab environment on AWS.  It attempts to strike a good balance between 
configurability and ease of use.

Cloudlab provisions a single /24 subnet in its own VPC on AWS and supports deploying up to 154 hosts into that subnet.

Notes:
- Only EBS instance types are supported
- All instances (hosts) will have an Amazon assigned public IP address and DNS name.
- Private ip addresses must be in the range 10.0.0.101 - 10.0.0.254  
- All hosts will run Amazon Linux 2, which is a yum based distribution derived from Ubuntu.
- All hosts can initiate connections to any server either in or outside of the private network
- All hosts accept inbound connections on port 22
- Other than port 22, hosts will only accept inbound connections on specific ports which can be configured per host
- Each environment provisioned with cloudlab will have its own ssh key which will be shared by all the hosts.


Hosts can be accessed via ssh using the provided key and "ec2-user"
(e.g.  `ssh -i my-lab-key.pem ec2-user@123.45.67.89`).


After provisioning is complete, Cloudlab will write an Ansible inventory file which can be used for further provisioning.
Cloudlab supports the idea of roles, which will be propagated to the Ansible inventory file.

# Setup

Cloudlab requires python 3.  It can be installed using pip.

```
pip install cloudlab
```

Installing cloudlab will install the aws cli if it is not already there.

Next you will need to configure the aws cli with your AWS access key and
secret access key so that it can access your account.  Cloudlab uses the
the aws cli and will have whatever privileges your cli has.  You can either
configure it with your root credentials or create a new IAM user and provide
those credentials.  If you create a new IAM user, it will need the following
permissions.

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

If your aws cli is not already configured, provide your credentials using the
command below.  They will be stored under the ".aws" folder in your home
directory.  Note that you will be prompted to provide a region but this is
only a default.  You can use cloudlab to deploy into any region.

```
aws configure  # follow the prompts ...
```
# Usage

Create a file called "cloudlab_config.yaml" in the current directory and edit it to describe the environment(s) you 
would like to provision.  An example is given below.

```yaml

---
  region: us-east-1
  servers:
    - instance_type: m5.xlarge
      private_ip_addresses: [101,102,103] # 3 servers like this - private IPs will be 10.0.0.101,102,103
      roles:
        - ClusterMember
    - instance_type: m5.xlarge
      private_ip_addresses: [111]         # 1 server like this - private IP will be 10.0.0.111
      roles:
        - ManCenter                       # Servers may have one or more roles
        - RawTransactionSource            # Roles must be alphanumeric - no underscores or hyphens 
        - ReportRunner
    - instance_type: m5.xlarge
      private_ip_addresses: [112]  
      roles:
        - TransactionClient
  open_ports:                             # Open ports are specified by role
    ClusterMember:
      - 5701
      - 5702
      - 5703
    ManCenter:
      - 8080
    RawTransactionSource: []              # configure no open ports like this
    ReportRunner: []                      # all servers will still listen on port 22 for SSH connections
    TransactionClient: []
```

Create an environment ...

```
cloudlab mkenv envdir
```

"envdir" should be an absolute or relative path.  The `basename(envdir)` will be used as the name of the environment 
and must be unique. 

The "envdir" directory will be created.  The process will fail if the directory already exists.

An Ansible inventory file containing both the public and private ip addresses will be written into 
"envdir" to faciliate managing the environment with  Ansible playbooks

```
cloudlab rmenv envdir
```

Will destroy a previously created environment.
