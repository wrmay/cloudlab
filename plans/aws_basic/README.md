# AWS Basic Plan

This plan supports deploying up to 154 hosts in a single /24 public subnet.

As well as the number of hosts, the region, availability zone and instance
type can be specified.  Only EBS instance types are supported. All instances
(hosts) will have an Amazon assigned public IP address and DNS name.  The hosts
will also have private ip addresses which will be assigned sequentially starting
with 10.0.0.101 and proceeding through 10.0.0.254.  Knowing the IP addresses
before provisioning makes it easier to construct clusters.  Hosts will have the
ability to connect to each other and out to the internet.  A list of inbound
ports can be specified.  All hosts will allow inbound connections on the
specified list of ports as well as on port 22. All hosts will run
Amazon Linux 2.

A key pair must be create in the Amazon region where the cluster will be
provisioned.  Access to all servers will be via passwordless ssh using the
specified key pair and "ec2-user" as shown below.

```
ssh -i my-key-pair.pem ec2-user@123.45.67.89
```
