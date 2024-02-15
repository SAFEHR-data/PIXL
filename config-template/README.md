# Configuration template

>[!WARNING]
> WORK IN PROGRESS

The PIXL project configuration template is written in [Pkl](https://pkl-lang.org/index.html) to
allow safe type checking and easy configuration.

## Installation

Follow the [Pkl installation instructions](https://pkl-lang.org/main/current/pkl-cli/index.html#installation)
for your platform.

## Usage

The `PixlConfig.pkl` file defines the configuration template for a PIXL project. For a new project,
create a new `.pkl` file and fill out the template like so:

```pkl
// my_project.pkl
amends "PixlConfig.pkl"

project = "My Project"
dicom_anon_profile {
    base_profile = "???"
    // extension_profile = "???" // optional
}
destination {
    dicom = "FTPS" // or None, Azure, DicomWeb
    parquet = "FTPS" // or Azure
}
```

Then, run the `pkl` CLI command to check the configuration:

```sh
pkl eval my_project.pkl
```

To generate the config in YAML format, run:

```sh
pkl eval -f yaml my_project.pkl >> my_project.yml
```

An example can be found in `example.pkl`.
