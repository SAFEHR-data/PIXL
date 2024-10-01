# UCLH Infrastructure setup instructions

## Install shared miniforge installation if it doesn't exist

Follow the suggestion for installing a central [miniforge](https://github.com/conda-forge/miniforge)
installation to allow all users to be able to run modern python without having admin permissions.

```shell
# Create directory with correct structure (only if it doesn't exist yet)
mkdir -p /gae/uv/bin
chgrp -R docker /gae/uv
chmod -R g+rwxs /gae/uv  # inherit group when new directories or files are created
setfacl -R -m d:g::rwX /gae/uv
# Install miniforge
wget "curl -LsSf https://astral.sh/uv/install.sh | env UV_INSTALL_DIR="/gae/uv/bin" sh"
```

The directory should now have these permissions

```shell
> ls -lah /gae/miniforge3/
total 0
drwxrws---+  3 spiatek1 docker  17 Sep 10 17:13 .
drwxrwx---. 11 root     docker 151 Sep 10 17:00 ..
drwxrws---+  2 spiatek1 docker  27 Sep 10 17:13 bin
```

## If you haven't just installed the miniforge yourself, update your configuration

Edit `~/.bash_profile` to add `/gae/uv/bin` to the PATH. For example:

```shell
PATH=$PATH:$HOME/.local/bin:$HOME/bin:/gae/uv/bin
```

Run the updated profile (or reconnect to the GAE) so that `uv` is in your PATH:

```shell
source ~/.bash_profile
```

## Create an instance for the GAE if it doesn't already exist

Select a place for the deployment. On UCLH infrastructure this will be in `/gae`, so `/gae/pixl_dev` for example.

```shell
mkdir /gae/pixl_dev
chgrp -R docker /gae/pixl_dev
chmod -R g+rwxs /gae/pixl_dev  # inherit group when new directories or files are created
setfacl -R -m d:g::rwX /gae/pixl_dev
```

Now clone the repository (or copy an existing deployment):

```shell
git clone https://github.com/UCLH-Foundry/PIXL.git /gae/pixl_dev
```

Finally, use `uv` to install Pythona, create a virtual environment, and install PIXL:

```shell
uv python install 3.11
uv venv --python 3.11
uv sync --frozen  # use --frozen so we do not update the dependecies in the uv.lock file
source .venv/bin/activate
```
