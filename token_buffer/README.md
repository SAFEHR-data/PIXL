# Token buffer

The token buffer is needed to limit the download rate for images from PAX/VNA. Current specification suggests that a 
rate limit of five images per second should be sufficient, however that may have to be altered dynamically through 
command line interaction. 

The current implementation of the token buffer uses the 
[token bucket implementation from Falconry](https://github.com/falconry/token-bucket/). Furthermore, the token buffer is
not set up as a service as it is only needed for the image download rate. 