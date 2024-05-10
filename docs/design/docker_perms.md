# Docker setup

Setup of user IDs, file permissions, and other related things in docker.

## Requirements and design considerations

### Docker containers should not run as root

Security. Different docker configs; see issue # for more

### Export temp dir needs to be readable by Export API container

The PIXL CLI is the only thing that writes into the Export temp dir, so it's up to the user
to make sure that it does so in such a way that it can be read by the Export API.
The Export API runs as a configurable user and group (see below), so it will depend
on which user is running the CLI, its umask settings, file permissions/ACLs, and perhaps
more as to whether it will work.


### PIXL_USER_UID and PIXL_USER_GID

During docker image build, a user called `pixl` and a group called `pixl` are created.
These variables control the numerical UID and GID that will be used.

This needs to be controlled because on the GAEs, docker is set up so that user IDs
on containers are the same as on the host. If you're UID 7001 on the container, then
you're 7001 on the host! So you will want to change these values to match which user
you want the PIXL containers to run as on the host. 
Ideally you'd create a service account especially for pixl, and then set its UID/GID
in these variables. The PIXL containers will still use the name `pixl`, but as long
as the numerical IDs match, it'll consider it to be the same user.

The variables are also used by the GHA system test to set up this user and group on
the GHA test runner, simulating how an admin would have set this up in production.

If you are running the system test on Windows or Mac, you should find it works fine.
On linux, you may have to ensure you have installed Docker in rootless mode, otherwise
you may have to do annoying things like modify your values of these variables to match
the UID/GID of your current username, or create a new user/group (called pixl) on your
machine with UID/GID 7001.




