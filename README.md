# connector-sekoia-io-xdr

This connector enable you to make full use of the SEKOIA.IO XDR platform.

It includes the following actions:

- Retrieve a list of alerts that could be filtered by `creation date`, `status name`, `status uuid`, `short id of the alerts`, and/or the `rule name`.
- Retrieve events from sekoia.io, the required parameters are: `query` to filter the events, `earliest_time` and `latest_time` that forms a date range to filter the search.
- Add a comment to an alert.
- Update the status of an alert.
- Retrieve a specific alert.
- Activate a countermeasure.
- Deny a countermeasure.
- Get a specific asset.
- Update an asset.
- Delete an asset. 


Further information about the installation of the `fortisoar_sdk` and more were provided by Fortinet through the following link:

https://fndn.fortinet.net/index.php?/tools/file/101-fortisoar%E2%84%A2-connector-sdk/

More details could be found in the fortisoar_sdk `README.md` file