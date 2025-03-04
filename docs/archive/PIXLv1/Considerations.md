## Risks and Considerations

### Technical Risks
The primary technical risk is overburdening the PACS & VNA and causing an adverse impact on the operational performance of these systems.  
To mitigate this risk, queries will be managed with a task queue. The system will enforce rate limiting of any commands sent to the PACS & VNA with an adapted [token bucket](https://en.wikipedia.org/wiki/Token_bucket) algorithm which can be adjusted at runtime in response to system load. A [circuit breaker](https://en.wikipedia.org/wiki/Circuit_breaker_design_pattern) will wrap the retrieval processes and act as fail-safe. Individual request retries will be subject to an [exponential backoff](https://en.wikipedia.org/wiki/Exponential_backoff) strategy.


### Security Considerations
#### Inbound access to the Cloud Environment in Azure  
It is expected that a VPN connection (or ExpressRoute connection) between the on-prem UCLH estate and Azure will not initially be available.  
Point-to-point firewall restrictions and Azure access tokens will manage secure communication between PIXL and the DICOM service.

#### Outbound access 
All outbound connections will be over HTTPS.
The existing proxy service will be relied upon to manage outbound access from the GAE.