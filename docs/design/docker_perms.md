# Docker setup

Setup of user IDs, file permissions, ACLs, and other related things in docker.

## Requirements and design considerations

### The aim - Docker containers should not run as root

Generally it's considered a bad idea to run anything as root that doesn't need it.
See "Principle of Least Privilege".

Bear in mind that if you're running as a user in the `docker` group, you might as well
be running as root, because you can create docker containers that run as root.

This page is mostly about how to not run containers as root, and the workarounds needed
to make it work.

### How do we run as non-root?

During the docker image build, a user called `pixl` and a group called `pixl` are created
*on the container*.
The build variables `PIXL_USER_UID` and `PIXL_USER_GID` control the numerical UID and GID that
will be mapped to those names. When the container is started, it runs as this user.

The numerical IDs need to be configurable because on the GAEs, docker is set up so that
there is no remapping between user IDs on containers and user IDs on the host.
If you're UID 7001 on the container, then
you're 7001 on the host! Although containers may interpret them as `pixl:pixl`, the host may
interpret them as another user/group, or as a missing user/group.
So you will want to change these values so PIXL can play nicely with your host.

### Doesn't this have some annoying side effects?

Yes, it means that files created on a mounted directory by a container will have the ownership
of (eg) 7001:7001.

And similarly the container will only be able to read (or write) files on a mounted directory
according to its UID/GID.

The host will map these numerical IDs according to its view of users and groups, as defined
in the usual way (`/etc/passwd` and `/etc/group`).

In the case of the Export API, it reads files from the export dir that were written by the CLI.
So, all files in the export temp dir need to be readable by the Export API container, and therefore
it matters as what user/group the CLI is run.

### Example

Imagine you are a user on the GAE with username `fred`, primary group `fred`, and supplementary
group `docker`.

When you run the CLI, it will run as fred:fred, and normally any files it creates would also have
this ownership. (ACLs defined in `/gae` will affect this however, so the files may have
a different group ownership, such as fred:docker)

There is a problem here in that the export API will likely be running as some other user/group,
so it will not be able to read the files.

Options for fixing:
* The CLI (or an ACL on the exports dir) makes the files world readable. Not ideal from a security
  pov.
* Relying on the existing ACL for `/gae` which gives files group ownership of `docker`, we run the
   Export API as the `docker` group, thus giving it read access to these files. However, this is
   very similar to running the container as root, which is what this whole thing is trying to avoid.
* Create a new group (`pixl`) on the GAE and add all pixl devs to it.
  Set an ACL on the exports dir that sets group ownership for all created files as `pixl`.
  Then we could set its GID in the env file so that the container runs as group `pixl`.
* Always build and run the containers as the same user that is running the CLI. You set the
  build vars `PIXL_USER_[UG]ID` to the numerical value of fred:fred. PIXL runs as you. When you run
  CLI, the files are owned by fred:docker, so export api can read them fine.


# What about system testing?

The build args are also used by the GHA system test workflow to set up this user and group on
the GHA test runner, simulating how a user might set this up in production.

Running the system test on Windows or Mac should be fine, but on linux, it might only work if Docker
is installed in rootless mode, otherwise you may have to do annoying things like modify your values
of these variables to match the UID/GID of your current username, or create a new user/group
(called pixl) on your machine with UID/GID 7001.


