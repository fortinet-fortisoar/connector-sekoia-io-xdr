## About the connector
SEKOIA.IO eXtended Detection and Response SaaS platform leverages Cyber Threat Intelligence to combine anticipation with automated incident response. SEKOIA.IO XDR offers open, transparent and flexible security oversight to break down silos and neutralise threats before impact, using intelligence. This connector facilitates automated operations related to alerts, assets and events.
<p>This document provides information about the SEKOIA.IO XDR Connector, which facilitates automated interactions, with a SEKOIA.IO XDR server using FortiSOAR&trade; playbooks. Add the SEKOIA.IO XDR Connector as a step in FortiSOAR&trade; playbooks and perform automated operations with SEKOIA.IO XDR.</p>
### Version information

Connector Version: 1.0.0


Authored By: SEKOIA.IO

Certified: No
## Installing the connector
<p>From FortiSOAR&trade; 5.0.0 onwards, use the <strong>Connector Store</strong> to install the connector. For the detailed procedure to install a connector, click <a href="https://docs.fortinet.com/document/fortisoar/0.0.0/installing-a-connector/1/installing-a-connector" target="_top">here</a>.<br>You can also use the following <code>yum</code> command as a root user to install connectors from an SSH session:</p>
`yum install cyops-connector-sekoia-io-xdr`

## Prerequisites to configuring the connector
- You must have the URL of SEKOIA.IO XDR server to which you will connect and perform automated operations and credentials to access that server.
- The FortiSOAR&trade; server should have outbound connectivity to port 443 on the SEKOIA.IO XDR server.

## Minimum Permissions Required
- N/A

## Configuring the connector
For the procedure to configure a connector, click [here](https://docs.fortinet.com/document/fortisoar/0.0.0/configuring-a-connector/1/configuring-a-connector)
### Configuration parameters
<p>In FortiSOAR&trade;, on the Connectors page, click the <strong>SEKOIA.IO XDR</strong> connector row (if you are in the <strong>Grid</strong> view on the Connectors page) and in the <strong>Configurations&nbsp;</strong> tab enter the required configuration details:&nbsp;</p>
<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>API Key<br></td><td>Specify the API key used to access the SEKOIA.IO XDR server to which you will connect and perform the automated operations.<br>
<tr><td>Verify Certificate<br></td><td>Specifies whether the SSL certificate for the server is to be verified or not.<br>
<tr><td>Proxy<br></td><td>Specifies whether the proxy for the server is to be verified or not.<br>
</tbody></table>
## Actions supported by the connector
The following automated operations can be included in playbooks and you can also use the annotations to access operations from FortiSOAR&trade; release 4.10.0 and onwards:
<table border=1><thead><tr><th>Function<br></th><th>Description<br></th><th>Annotation and Category<br></th></tr></thead><tbody><tr><td>Get Events<br></td><td>Search events according the query from SEKOIA.IO XDR based on the query, earliest time, and latest time you have specified.<br></td><td>get_events <br/>Investigation<br></td></tr>
<tr><td>List Alerts<br></td><td>Retrieves all alerts from SEKOIA.IO XDR based on the input parameters that you have specified.<br></td><td>list_alerts <br/>Investigation<br></td></tr>
<tr><td>Get Alert<br></td><td>Retrieves an specific alert from SEKOIA.IO XDR based on the alert uuid and other input parameters that you have specified. <br></td><td>get_alert <br/>Investigation<br></td></tr>
<tr><td>Update Alert Status<br></td><td>Updates a specific alert in SEKOIA.IO XDR based on the alert identifier and other input parameters that you have specified.<br></td><td>update_alert_status <br/>Investigation<br></td></tr>
<tr><td>Add Comment to Alert<br></td><td>Add a new comment to the specific alert in SEKOIA.IO XDR based on the alert identifier, comment, and other input parameter you have specified.<br></td><td>add_comment_to_alert <br/>Investigation<br></td></tr>
<tr><td>Get Asset<br></td><td>Retrieves an specific asset from SEKOIA.IO XDR based on the asset uuid you have specified.<br></td><td>get_asset <br/>Investigation<br></td></tr>
<tr><td>Update Asset<br></td><td>Updates a specific asset in SEKOIA.IO XDR based on the asset uuid, asset type uuid, asset type name, and other input parameters that you have specified.<br></td><td>update_asset <br/>Investigation<br></td></tr>
<tr><td>Delete Asset<br></td><td>Delete an specific asset from SEKOIA.IO XDR based on the asset uuid you have specified.<br></td><td>delete_asset <br/>Investigation<br></td></tr>
<tr><td>Activate a Countermeasure<br></td><td>Activate a countermeasure in SEKOIA.IO XDR based on the countermeasure uuid, comment and other input parameters that you have specified.<br></td><td>activate_countermeasure <br/>Investigation<br></td></tr>
<tr><td>Deny a Countermeasure<br></td><td>Deny a countermeasure in SEKOIA.IO XDR based on the countermeasure uuid, comment and other input parameters that you have specified.<br></td><td>deny_countermeasure <br/>Investigation<br></td></tr>
</tbody></table>
### operation: Get Events
#### Input parameters
<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>Query<br></td><td>The query to search events<br>
</td></tr><tr><td>Earliest Time<br></td><td>The earliest time of the time range of the search<br>
</td></tr><tr><td>Latest Time<br></td><td>The latest time of the time range of the search<br>
</td></tr></tbody></table>
#### Output

 The output contains a non-dictionary value.
### operation: List Alerts
#### Input parameters
<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>Filter by Status Identifier<br></td><td>Filter alerts according the identifiers of their status.<br>
</td></tr><tr><td>Filter by Status Name<br></td><td>Filter alerts according the name of their status.<br>
</td></tr><tr><td>Short ID<br></td><td>Filter alerts according their short_id.<br>
</td></tr><tr><td>Rule UUID<br></td><td>Filter alerts according the identifiers of rules that raised them<br>
</td></tr><tr><td>Rule Name<br></td><td>Filter alerts according the names of rules that raised them<br>
</td></tr><tr><td>Created At<br></td><td>Filter alerts according their creation date<br>
</td></tr></tbody></table>
#### Output

 The output contains a non-dictionary value.
### operation: Get Alert
#### Input parameters
<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>Alert UUID<br></td><td>The unique identifier of the alert (uuid or short_id)<br>
</td></tr><tr><td>Include Comments<br></td><td>Option to include comments of the alert<br>
</td></tr><tr><td>Include STIX<br></td><td>Option to include the stix of the alert<br>
</td></tr><tr><td>Include History<br></td><td>Option to include the history of the alert<br>
</td></tr><tr><td>Include Countermeasures<br></td><td>Option to include the countermeasures of the alert<br>
</td></tr></tbody></table>
#### Output

 The output contains a non-dictionary value.
### operation: Update Alert Status
#### Input parameters
<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>Alert Identifier<br></td><td>The unique identifier of the alert (uuid or short_id)<br>
</td></tr><tr><td>Action UUID<br></td><td>The unique identifier of the action<br>
</td></tr><tr><td>Comment<br></td><td>The comment to associate to the action<br>
</td></tr></tbody></table>
#### Output

 The output contains a non-dictionary value.
### operation: Add Comment to Alert
#### Input parameters
<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>Alert Identifier<br></td><td>The unique identifier of the alert (uuid or short_id)<br>
</td></tr><tr><td>Comment<br></td><td>The content of the comment<br>
</td></tr><tr><td>Author<br></td><td>The author of the comment<br>
</td></tr></tbody></table>
#### Output

 The output contains a non-dictionary value.
### operation: Get Asset
#### Input parameters
<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>Asset UUID<br></td><td>The unique identifier of the asset<br>
</td></tr></tbody></table>
#### Output

 The output contains a non-dictionary value.
### operation: Update Asset
#### Input parameters
<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>Asset UUID<br></td><td>The unique identifier of the asset<br>
</td></tr><tr><td>Asset Name<br></td><td>The name of the asset<br>
</td></tr><tr><td>Asset Type UUID<br></td><td>The uuid of the asset type<br>
</td></tr><tr><td>Asset Type Name<br></td><td>The name of the asset type<br>
</td></tr><tr><td>Asset Criticity<br></td><td>The criticity of the asset<br>
</td></tr><tr><td>Asset Description<br></td><td>The description of the asset<br>
</td></tr><tr><td>Asset Attributes<br></td><td>The attributes of the asset<br>
</td></tr><tr><td>Asset Keys<br></td><td>The keys of the assets<br>
</td></tr><tr><td>Asset Owners<br></td><td>the owners of the assets<br>
</td></tr></tbody></table>
#### Output

 The output contains a non-dictionary value.
### operation: Delete Asset
#### Input parameters
<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>Asset UUID<br></td><td>The unique identifier of the asset<br>
</td></tr></tbody></table>
#### Output

 The output contains a non-dictionary value.
### operation: Activate a Countermeasure
#### Input parameters
<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>Countermeasure UUID<br></td><td>The unique identifier of the countermeasure<br>
</td></tr><tr><td>Comment<br></td><td>The content of the comment to associate to the countermeasure<br>
</td></tr><tr><td>Author<br></td><td>The author of the comment to associate to the countermeasure<br>
</td></tr></tbody></table>
#### Output

 The output contains a non-dictionary value.
### operation: Deny a Countermeasure
#### Input parameters
<table border=1><thead><tr><th>Parameter<br></th><th>Description<br></th></tr></thead><tbody><tr><td>Countermeasure UUID<br></td><td>The unique identifier of the countermeasure<br>
</td></tr><tr><td>Comment<br></td><td>The content of the comment to associate to the countermeasure<br>
</td></tr><tr><td>Author<br></td><td>The author of the comment to associate to the countermeasure<br>
</td></tr></tbody></table>
#### Output

 The output contains a non-dictionary value.
## Included playbooks
The `Sample - sekoia-io-xdr - 1.0.0` playbook collection comes bundled with the SEKOIA.IO XDR connector. These playbooks contain steps using which you can perform all supported actions. You can see bundled playbooks in the **Automation** > **Playbooks** section in FortiSOAR<sup>TM</sup> after importing the SEKOIA.IO XDR connector.

- Get Events
- List Alerts
- Get Alert
- Update Alert Status
- Add Comment to Alert
- Get Asset
- Update Asset
- Delete Asset
- Activate a Countermeasure
- Deny a Countermeasure

**Note**: If you are planning to use any of the sample playbooks in your environment, ensure that you clone those playbooks and move them to a different collection, since the sample playbook collection gets deleted during connector upgrade and delete.
