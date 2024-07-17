# Create Python virtual environment

## Using conda
```
conda create -n "pixlVE" python=3.12 pip -c conda-forge
conda activate pixlVE
conda list -n pixlVE #to check installed packages
conda deactivate && conda remove -n pixlVE --all #in case you want to remove it
```

## Using python virtual environment
```
# Installing dependencies in Ubuntu 22.04
sudo apt-get install -y python3-pip
sudo apt-get install -y python3-venv
# Create path for venv
cd $HOME
mkdir *VE
cd *VE
# Create virtual environment
python3 -m venv pixlVE
source pixlVE/bin/activate
```

