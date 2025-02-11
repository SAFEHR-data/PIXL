# UCLH Infrastructure setup instructions

## GAE environment setup using `uv`

If not already done, follow the
[non-project specific guidance on setting up shared virtual environments with uv](https://uclh.slab.com/posts/shared-virtual-python-environments-with-uv-u7pa2fv4)
to allow all users to be able to run modern Python without having admin permissions.

## Create a PIXL instance for the GAE
If it doesn't already exist, or you want to create a new instance of PIXL, first
select a place for the deployment.
On UCLH infrastructure this will be in `/gae`, so `/gae/pixl_dev` for example.

Follow the [per-project setup guidance](https://uclh.slab.com/posts/shared-virtual-python-environments-with-uv-u7pa2fv4#hizbb-per-project-setup-tasks)
in the same document as above to create this directory with the correct permissions.
Then you can do a simple `git clone` of this repo inside this directory.
