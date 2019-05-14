# Cloudlab Overview

Cloudlab allows you to quickly provision a lab environment on AWS.  It attempts to strike a good balance between 
configurability and ease of use.

Cloudlab provisions a single /24 subnet in its own VPC on AWS and supports deploying up to 154 hosts into that subnet.

The number of hosts, the region, and instance type can be specified.   Only EBS instance types are supported. All 
instances (hosts) will have an Amazon assigned public IP address and DNS name.  Each host will also have private ip 
addresses which will be assigned sequentially starting with 10.0.0.101 and proceeding through 10.0.0.254.  Knowing the 
IP addresses before provisioning makes it easier to construct clusters.  

Hosts will have the ability to connect to each other on any port using their private IP addresses. All hosts can also 
create outbound connections to the internet.  Inbound connections are limited to a list of ports which can be specified 
at the time of provisioning.  Hosts will allow inbound connections from outside the private network only on a limited 
list of ports that can be defined.  All hosts allow inbound connections from anywhere on port 22.

Each environment provisioned with cloudlab will have its own ssh key which will be shared by all the hosts.

All hosts will run Amazon Linux 2, which is a yum based distribution derived from Ubuntu.

Hosts can be accessed via ssh using the provided key and "ec2-user"
(e.g.  `ssh -i my-lab-key.pem ec2-user@123.45.67.89`).

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
  region: us-east-2
  instance_count: 3
  instance_type: m4.large
  open_ports:
    - 80     #there is no need to specify 22 , it is open by default
    - 8080

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
