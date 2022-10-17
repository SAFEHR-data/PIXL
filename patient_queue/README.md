# Patient Queue

Service that holds information on what images and record data needs to be downloaded. At the moment it is envisaged to 
have two separate queues for images and EHR data so that failed downloads can be pushed back to the queue.

Realised with Pulsar as a messaging service.