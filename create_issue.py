#!/usr/bin/env python3
# -*-encoding: utf-8-*-
# Author: Vladislav Gusak
#
# Usage: ./create_issue.py  --set project=PRJ --set issuetype="Task" --set components="Domain_X" --set summary="Categorize defects" --set assignee="Vladislav Gusak" --set Sprint=382 --set "Epic Link"=PRJ-15465" --set timetracking=4h
# Usage: ./create_issue.py  --set project=PRJ --set issuetype="Feature" --set summary="[PoC] Some feature" --set assignee="Vladislav Gusak" --set labels=PoC_Mandatory_Feature --set labels=high_priority --link PRJ-236:"Is part of" --link PRJ-104:"FF-depends on" --set "IP Type"="Customer Specific IP"

import argparse
import json
import re

from jira.client import JIRA

from colored_log import log
from jira_utils import *

from enum import Enum


def parse_args():
    parser = argparse.ArgumentParser(
        description='Creates issue with provided properties and liks.')
    parser.add_argument(
        '-s', '--jira-server',
        dest='jira_server',
        help='JIRA API server address (overrides JIRA_API_SERVER environment variable)',
        required=False)
    parser.add_argument(
        '-u', '--jira-user',
        dest='jira_user',
        help='JIRA API login username (overrides JIRA_API_USERNAME environment variable)',
        required=False)
    parser.add_argument(
        '-t', '--jira-token',
        dest='jira_token',
        help='JIRA API secure token (overrides JIRA_API_TOKEN environment variable)',
        required=False)
    parser.add_argument('--show_fields', help='Show all fields(for specific information: set issue_type and issue_project)', required=False, action='store_true')
    parser.add_argument('--issue_type', help='Show fields of specific issue type', required=False, type=str, dest='issue_type')
    parser.add_argument('--issue_project', help='Show fields of specific project(does not work without --issue_type)', required=False, type=str, dest='issue_project')
    parser.add_argument("--set",
                        metavar="FIELD=VALUE",
                        nargs='+',
                        action='append',
                        help="Set a number of key-value pairs "
                             "(do not put spaces before or after the = sign). "
                             "If a value contains spaces, you should define "
                             "it with double quotes: "
                             'field="this is a sentence". Note that '
                             "values are always treated as strings.")
    parser.add_argument("--link",
                        metavar="ISSUE:LINK",
                        nargs='+',
                        action='append',
                        help="ISSUE_ID:LINK, example: PRJ-100:\"Is part of\"")

    return parser.parse_args()

def parse_item(s, delimiter):
    """
    Parse a key, value pair, separated by '='
    That's the reverse of ShellArgs.

    On the command line (argparse) a declaration will typically look like:
        foo=hello
    or
        foo="hello world"
    """
    items = s.split(delimiter)
    key = items[0].strip() # we remove blanks around keys, as is logical
    if len(items) > 1:
        # rejoin the rest:
        value = delimiter.join(items[1:])
    return (key, value)

def parse_items_for_set(items):
    """
    Parse a series of key-value pairs and return a dictionary
    """
    d = {}

    if items:
        for item in items:
            key, value = parse_item(item[0], '=')

            if key not in d:
                d[key] = list()
 
            d[key].append(value)
    return d

def parse_items_for_link(items):
    """
    Parse a series of key-value pairs and return a dictionary
    """
    d = {}

    if items:
        for item in items:
            key, value = parse_item(item[0], ':')
            d[key] = value
    return d

class JiraFieldType(Enum):
    NONE = -1
    ARRAY = 0
    STRING = 1
    ENUM = 2
    TIME_TRACKING = 3

class JiraAllowedValueInformation:
    def __init__(self, information):
        self.information = information

    def get_raw(self):
        return self.information
    
    def get_value(self):
        if 'value' in self.information:
            return self.information['value']
        elif 'name' in self.information:
            return self.information['name']
        
        log.error("No value or name fields in allowed values information: {0}".format(self.get_raw()))
        exit()
        
    def get_id(self):
        return self.information['id']

class JiraFieldInformation:
    def __init__(self, information):
        self.information = information
    
    def get_raw(self):
        return self.information

    def get_name(self):
        return self.information['name']
    
    def get_key(self):
        return self.information['key']
    
    def get_type(self):
        type = self.information['schema']['type']

        if type == "array":
            return JiraFieldType.ARRAY
        elif type == "string":
            return JiraFieldType.STRING
        elif "allowedValues" in self.information:
            return JiraFieldType.ENUM
        
        return JiraFieldType.NONE
    
    def get_items_type(self):
        if "items" not in self.information['schema']:
            return JiraFieldType.NONE
        
        type = self.information['schema']['items']

        if type == "array":
            return JiraFieldType.ARRAY
        elif type == "string":
            return JiraFieldType.STRING
        elif "allowedValues" in self.information:
            return JiraFieldType.ENUM
        
        return JiraFieldType.NONE
    
    def get_allowed_values(self):
        if self.get_type() != JiraFieldType.ENUM and self.get_items_type() != JiraFieldType.ENUM:
            return None

        allowed_values = {}
        for allowed_value in self.information['allowedValues']:
            allowed_value = JiraAllowedValueInformation(allowed_value)
            allowed_values[allowed_value.get_value()] = allowed_value
        
        return allowed_values
        

class Converter:
    def __init__(self, jira):
        self.jira = jira

    def values_to_project(self, values, field_information):
        return {'key': get_jira_project(jira, values[0]).key}

    def values_to_issuetype(self, values, field_information):
        return {'name': values[0]}

    def values_to_components(self, values, field_information):
        return [{'name': values[0]}]

    def values_to_assignee(self, values, field_information):
        return {'accountId': get_jira_user(self.jira, values[0]).accountId}

    def strs_to_int(self, values, field_information):
        return int(values[0])
    
    def values_to_timetracking(self, values, field_information):
        return {"originalEstimate": values[0]}
    
    def values_to_labels(self, values, field_information):
        return [values[0]]
    
    def values_to_enum(self, values, field_information):
        allowed_values = field_information.get_allowed_values()

        if values[0] not in allowed_values:
            log.error("No value: {0} in field: {1}".format(values[0], field_information.get_value()))
            exit()
        
        return {"id": allowed_values[values[0]].get_id()}
    
    def values_to_array(self, values, field_information):
        if field_information.get_items_type() == JiraFieldType.ENUM:
            array = list()
 
            for value in values:
                array.append(self.values_to_enum([value], field_information))
            return array
        else:
            return values


def make_name_predicate(name):
    return lambda field_information: field_information.get_key() == name

def make_array_predicate():
    return lambda field_information: field_information.get_type() == JiraFieldType.ARRAY

def make_enum_predicate():
    return lambda field_information: field_information.get_type() == JiraFieldType.ENUM

def make_predicates_and_convertors_list(converter):
    return [
        {"predicate": make_name_predicate('project'),           "converter": converter.values_to_project},
        {"predicate": make_name_predicate('issuetype'),         "converter": converter.values_to_issuetype},
        {"predicate": make_name_predicate('assignee'),          "converter": converter.values_to_assignee},
        {"predicate": make_name_predicate('customfield_10113'), "converter": converter.strs_to_int},
        {"predicate": make_name_predicate('timetracking'),      "converter": converter.values_to_timetracking},
        {"predicate": make_enum_predicate(),                    "converter": converter.values_to_enum},
        {"predicate": make_array_predicate(),                   "converter": converter.values_to_array}
    ]

def get_issue_by_issuetype_and_project(jira, issuetype, project):
    issue_project_search_str = ''
    if project is not None and len(project) != 0:
        issue_project_search_str = 'AND project={0}'.format(project)

    jql_filter = 'issuetype={0} {1}'.format(issuetype, issue_project_search_str)

    issues = jira.search_issues(jql_filter, 0, 1, fields = '')
    if (len(issues) == 0):
        return None
    
    return issues[0]

def get_jira_fields_information(issue):
    allfields_json = jira.editmeta(issue)['fields']
    fields_dict = {}

    for field_information in allfields_json:
        fields_dict[field_information] = JiraFieldInformation(allfields_json[field_information])
    
    return fields_dict

def generate_jira_fields_information_from_general_source(information):
    fields_dict = {}

    for field_information in information:
        field = JiraFieldInformation(field_information)
        fields_dict[field.get_key()] = field
    
    return fields_dict

if __name__ == '__main__':
    args = parse_args()

    jira_login_info = make_jira_login_info(args.jira_server, args.jira_user, args.jira_token)

    jira = init_jira_api(jira_login_info)

    allfields=jira.fields()
    fields_general_information_dict = generate_jira_fields_information_from_general_source(allfields)

    fields_ids_map = {field['id']:field['name'] for field in allfields}
    fields_names_map = {field['name']:field['id'] for field in allfields}

    fields_ids_map_all_data = {}

    if args.show_fields:
        if args.issue_type is None:
            for field in allfields:
                fields_ids_map_all_data[field['id']] = {}
                fields_ids_map_all_data[field['id']]['name'] = field['name']
                if "schema" in field:
                    fields_ids_map_all_data[field['id']]['schema'] = field['schema']

            log.debug(json.dumps(fields_ids_map_all_data, indent=4, sort_keys=True))
            exit()
        else:
            issue = get_issue_by_issuetype_and_project(jira, args.issue_type, args.issue_project)

            if issue is None:
                log.error("Wasn't found issues with type: {0}".format(args.issue_type))
                exit()

            allfields = jira.editmeta(issue)['fields']
            log.debug(json.dumps(allfields, indent=4, sort_keys=True))
            exit()

    fields_and_values = parse_items_for_set(args.set)
    all_ids = list(fields_and_values.keys())

    if "issuetype" not in all_ids or "project" not in all_ids:
        log.error("Fields are not set: issuetype and/or project")
        exit()

    similar_issue = get_issue_by_issuetype_and_project(jira, fields_and_values['issuetype'][0], fields_and_values['project'][0])
    fields_information_dict = {**fields_general_information_dict, **get_jira_fields_information(similar_issue)}

    converter = Converter(jira)
    predicates_and_convertors_list = make_predicates_and_convertors_list(converter)

    for id in all_ids:
        if id in fields_names_map:
            fields_and_values[fields_names_map[id]] = fields_and_values.pop(id)
        elif id not in fields_ids_map:
            log.error("Not found field: " + id)
            exit()

    final_fields = {}
    for field, values in fields_and_values.items():
        predicate_found = False
        if field not in fields_information_dict:
            log.error("Information not found for field: " + field)
            exit()
        field_information = fields_information_dict[field]

        for predicate_and_converter in predicates_and_convertors_list:
            if (predicate_and_converter['predicate'](field_information)):
                final_fields[field] = predicate_and_converter['converter'](values, field_information)
                predicate_found = True
                break
            
        if predicate_found == False:
            final_fields[field] = values[0]

    log.debug(json.dumps(final_fields, indent=4, sort_keys=True))
    links = parse_items_for_link(args.link)

    try:
        issue = jira.create_issue(final_fields)
        log.info("Successfully created a new issue: " + make_jira_issue_link(jira_login_info.server, issue.key))
        link_issues(jira, issue, links)
    except Exception as e:
        log.error("Failed to create issue. Error: " + str(e))
