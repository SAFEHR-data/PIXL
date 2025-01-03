# ORTHANC instances

PIXL defines 2 types of ORTHANC instances:

- `orthanc-raw`: This instance is used to store the raw DICOM files, acting as a cache before
  transfering the images to the `orthanc-anon` instance
- `orthanc-anon`: This instance is used to de-identify the DICOM images and upload them to their
  final destination

For both instances we define a plugin in `orthanc-*/plugin/pixl.py` that implements the custom
functionality .

## 'PIXL/orthanc' Directory Contents

<details>
<summary>
<h3> Subdirectories with links to the relevant README </h3> 

</summary>

[assets](./assets/README.md)

[orthanc-anon](./orthanc-anon/README.md)

[orthanc-raw](./orthanc-raw/README.md)

</details>

<details>
<summary>
<h3> Files </h3> 

</summary>

| **User docs** |
| :--- |
| README.md |

</details>


