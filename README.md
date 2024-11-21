# Cloudlab Overview

Cloudlab allows you to quickly provision a lab environment on AWS.  By adopting a somewhat opinionated approach, 
It attempts to strike a good balance between configurability and ease of use.

Cloudlab provisions a single VPC on AWS with a /16 private address space.  Within the VPC, 1 or more subnets can be 
configured.  All subnets are public and all have their own /24 address space inside the VPC.  All machines are assigned 
a role.  The machine type, image and a list of open ports are configured at the role level to avoid redundant 
configuration.

After successful deployment, cloudlab writes an `inventory.yaml` file,  which list the public and private ips of all 
servers, grouped by role.  The inventory file is suitable for use with Ansible.

A sample configuration for deploying 5 servers to 2 subnets is shown below.
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

Other Notes:
- All instances (hosts) will have an Amazon assigned public IP address and DNS name.
- All hosts can initiate outbound connections to any other server either in or outside of the VPC
- All hosts can receive connections on any port, from any other server in the VPC
- All hosts accept inbound connections on port 22
- Other than port 22, hosts will only accept inbound connections on specific ports which can be configured per role
- Each environment provisioned with cloudlab will have its own ssh key which will be shared by all the hosts.
- AMIs are specified by "name" rather than the typical "ami_id", which is region specific.  At deploy time, the 
name is translated to a region specific ami_id.  This makes the cloudlab configuration easier to port to another
region.

# Setup

Cloudlab requires python 3.  

It can be installed using pip.

```
pip install cloudlab
```

Cloudlab requires the aws cli to be present.  See https://docs.aws.amazon.com/cli/latest/userguide/cli-chap-getting-started.html 
for installation instructions.

The AWS CLI will need to be configured with your credentials so it can access your AWS account.
If your aws cli is not already configured, provide your credentials using the `aws configure` command or, 
if sso is configured, `aws sso login`

Cloudlab will have whatever privileges your cli has.  The snippet below is an IAM policy describing the permissions
needed by cloudlab.

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

# Usage

## Define your environment
Create a file called "cloudlab_config.yaml" in the current directory and edit it to describe the environment you
would like to provision.  See the example above.  You can also create a sample configuration file by running 
`cloudlab sample > cloudlab_config.yaml`.  See the comments in the sample file for details.

## Create a new environment

```
cloudlab mkenv <envdir>
```

"envdir" should be an absolute or relative path.  The name of the directory, without any path,  will be used as the 
name of the environment and the name must be unique. The "envdir" directory will be created.  The process 
will fail if the directory exists.

You can generate a CloudFormation template and skip the provisioning step by adding the `--no-provision` flag as 
shown below.

```
cloudlab mkenv <envdir> --no-provision 
```
## Destroy an environment

```
cloudlab rmenv <envdir>
```

This command is idempotent.  It will not fail if the environment does not exist.

## Update an environment

Update `cloudlab_config.yaml` with your changes and run ...

```
cloudlab update <envdir>
```

# Release Notes

## v1.2.0 is a major update
- default plan now includes multiple subnets
- configuration format has changed to allow the specification of subnets 
- the `--plan` option allows alternate templates to be used although there currently are none.
- the `cloudlab sample` will output a sample configuration file
- removed dependency on methods in setuptools

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
