# Jira Create issue script
## Agenda
create_issue.py script creates Jira issues from fields and links

## Install
```
sudo pip3 install jira jedi==0.17.2 IPython
```

## Preconditions
### Best choice
To use script you need set in your ~/.bashrc
```
export JIRA_API_SERVER=https://atlassian.net
export JIRA_API_USERNAME=name.surname@mail.com
export JIRA_API_TOKEN=PUT_YOUR_SECURE_API_TOKEN_HERE
```
Note: to get API token: https://support.atlassian.com/atlassian-account/docs/manage-api-tokens-for-your-atlassian-account/

### Workaround
You also can set these information in args of script:

```
--jira-server <JIRA_API_SERVER> --jira-user <JIRA_API_USERNAME> --jira-token <JIRA_API_TOKEN>
```

## Instruction
### Basic
To set field: <code>--set FIELD_ID=VALUE</code>, Example: <code>--set issuetype="Item Group"</code>, <code>--set timetracking=4h</code><br />
To set links: <code>--link ISSUE_ID:LINK_TYPE</code>, Example: <code>--link PRJ-110:"Is part of"</code><br />

As the name of fields you can use visible name or key(API) name. To check such information see section: Fields information

### Example of usage:<br />
```./create_issue.py  --set project=PRJ --set issuetype="Task" --set components="Domain_X" --set summary="Categorize defects" --set assignee="Vladislav Gusak" --set Sprint=382 --set "Epic Link"=PRJ-15465" --set timetracking=4h```<br />
<br />
```./create_issue.py  --set project=PRJ --set issuetype="Feature" --set summary="[PoC] Some feature" --set assignee="Vladislav Gusak" --set labels=PoC_Mandatory_Feature --set labels=high_priority --link PRJ-236:"Is part of" --link PRJ-104:"FF-depends on" --set "IP Type"="Customer Specific IP"```<br />

### Get fields information<br />
General information:<br />
```./create_issue.py --show_fields```<br />
Specific for the issue type(with enum values and so on):<br />
```./create_issue.py --show_fields --issue_type Task --issue_project PRJ```<br />
Note: for specific information -- it requires to have minimum 1 issue in space with this issue type<br />
