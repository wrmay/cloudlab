# Cloudlab Overview

Cloudlab allows you to quickly provision a lab environment on AWS.  It attempts
to strike a good balance between configurability and ease of use.

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

The first thing you will need to do is select your plan from the options
documented below. 
