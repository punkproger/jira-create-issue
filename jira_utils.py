#!/usr/bin/env python3
# -*-encoding: utf-8-*-

import os

from collections import namedtuple
from jira.client import JIRA
from jira.resources import User

from colored_log import log

JiraLoginInfo = namedtuple("JiraLoginInfo", ['server', 'user', 'token'])

# Exception for undefined environment variable
class UndefinedVariable(Exception):
    def __init__(self, var_name):
        self.message = var_name + ' variable is not specified'

def make_jira_login_info(in_server = None, in_user = None, in_token = None):
    '''
    Makes Jira login info structure JiraLoginInfo from input arguments
    or environment variables, if arguments are not valid.

    :param in_server: input Jira server address
    :param in_user: input Jira username (email)
    :param in_token: input Jira API secure token
    :return: Jira login info structure
    '''
    server = in_server
    if server is None:
        server = os.environ.get('JIRA_API_SERVER')
        if server is None:
            raise UndefinedVariable('JIRA_API_SERVER')
    if len(server) == 0:
        raise ValueError('Jira API server name is empty')

    user = in_user
    if user is None:
        user = os.environ.get('JIRA_API_USERNAME')
        if user is None:
            raise UndefinedVariable('JIRA_API_USERNAME')
    if len(user) == 0:
        raise ValueError('Jira API user name is empty')

    token = in_token
    if token is None:
        token = os.environ.get('JIRA_API_TOKEN')
        if token is None:
            raise UndefinedVariable('JIRA_API_TOKEN')
    if len(token) == 0:
        raise ValueError('Jira API secure token string is empty')

    return JiraLoginInfo(server, user, token)

def init_jira_api(login_info):
    '''
    Initializes Jira API with the provided login info.

    :param login_info: login info structure of type JiraLoginInfo
    :return: initialized Jira API instance
    '''
    jira = JIRA(server=login_info.server, basic_auth=(login_info.user, login_info.token))
    log.info('Jira login successful (server=' + login_info.server +
             ', username=' + login_info.user + ')')
    return jira

def get_jira_project(jira, jira_project_key):
    ''' Get Jira Project object by the given project key '''
    jira_project = None
    try:
        jira_project = jira.project(jira_project_key)
        log.info("Successfully acquired project info: key='{0}', name='{1}'"
                 .format(jira_project.key, jira_project.name))
    except Exception as e:
        log.error("Failed to find Jira project with key='{0}'. Error: {1}"
                  .format(jira_project_key, str(e)))
    return jira_project

def get_jira_component(jira, project_key, component_name):
    ''' Get Jira Component object by the given project key and component name '''
    try:
        project_components = jira.project_components(project_key)
        log.info("Successfully acquired project components list of size={0}"
                 .format(len(project_components)))
        for component in project_components:
            if component.name == component_name:
                log.info("Successfully found project component '{0}'".format(str(component)))
                return component
    except Exception as e:
        log.error("Failed to get Jira components for project_key='{0}'. Error: {1}"
                  .format(project_key, str(e)))
    return None

def get_jira_user(jira, user_name):
    ''' Get Jira User object by the given user email address '''
    log.info("Searching for user with email='{0}'".format(user_name))
    user = None
    try:
        found_users = jira._fetch_pages(User, None, 'user/search', 0, 1, {"query": user_name})
        print(found_users)
        if len(found_users) != 0 and (found_users[0].emailAddress == user_name or found_users[0].displayName == user_name):
            user = found_users[0]
            log.info("Successfully found user: " + str(user))
    except Exception as e:
        log.error("Failed to find Jira user. Error: " + str(e))
    if user is None:
        log.warn("Failed to find user for the given email='{0}'".format(user_name))
    return user

def get_jira_agile_board(jira, board_name):
    ''' Get Jira Agile board by its name '''
    log.info("Searching for Jira Agile board with name='{0}'".format(board_name))
    try:
        # Old private GreenHopper API is used, so all parameters will be ignored
        all_boards = jira.boards()
        for board in all_boards:
            log.info("Found Agile board: name='{0}', id={1}".format(board.name, board.id))
            if board.name == board_name:
                log.info("Successfully found Agile board: name='{0}', id={1}"
                         .format(board.name, board.id))
                return board
    except Exception as e:
        log.error("Failed to find Jira Agile board. Error: " + str(e))
    return None

def get_jira_sprints(jira, board_id):
    '''
    Get Jira sprints available in Agile board identified by board id.

    :param jira: Jira API instance
    :param board_id: Jira Agile board id
    :return: sprints dictionary {name -> info}. Empty if something went wrong or board is empty.
    '''
    log.info("Requesting Jira sprints by Agile board id={0}".format(board_id))
    try:
        sprints = jira.sprints_by_name(board_id)
        log.info("Successfully acquired sprints, count={0}".format(len(sprints)))
        return sprints
    except Exception as e:
        log.error("Failed to find Jira Agile board. Error: " + str(e))
    return {}

def search_all_issues(jira, search_str, fields = ''):
    ''' Helper issue search method not limited by request block size '''
    block_size = 100
    block_idx = 0
    all_issues = []
    while True:
        start_idx = block_size * block_idx
        issues = jira.search_issues(search_str, start_idx, block_size, fields = fields)
        if len(issues) == 0:
            return all_issues
        all_issues += issues
        block_idx += 1
    return all_issues

def search_issue_by_summary(jira, jira_project_key, summary_search_str, issue_summary):
    '''
    Search issue within the given project by specified summary

    :param jira: Jira API instance
    :param jira_project_key: Jira project key
    :param summary_search_str: short search string for issue summary (without special symbols like '[')
    :param issue_summary: full issue summary to compare with
    :return: issue matching the given summary or None if no such issue was found
    '''
    log.info("Searching issue by summary seach string '{0}'".format(summary_search_str))
    found_issues = search_all_issues(
        jira,
        "project={0} and summary~'{1}'".format(jira_project_key, summary_search_str),
        'summary')
    log.info("Found {0} Jira issue(s) with summary matching string '{1}'"
             .format(len(found_issues), summary_search_str))
    for issue in found_issues:
        if issue.fields.summary == issue_summary:
            return issue
    return None

def make_jira_issue_link(jira_server, issue_key):
    ''' Creates a web server link to Jira issue by the given issue key '''
    return jira_server + '/browse/' + issue_key

def link_epic_to_feature(jira, jira_epic, jira_feature):
    ''' Links Jira epic to the given feature '''
    try:
        jira.create_issue_link('Is part of', jira_epic.key, jira_feature.key)
        log.info("Successfully linked epic key='{0}' to a feature key='{1}'"
                 .format(jira_epic.key, jira_feature.key))
    except Exception as e:
        log.error("Failed to link epic to a feature. Error: " + str(e))

def link_issue(jira, origin_issue, destination_issue, link_type_str):
    ''' Links Jira <origin_issue> issue to the <destination_issue> issue with <link_type_str> issue type'''
    try:
        jira.create_issue_link(link_type_str, origin_issue.key, destination_issue.key)
        log.info("Successfully linked epic key='{0}' to a feature key='{1}', by type='{2}'"
                 .format(origin_issue.key, destination_issue.key, link_type_str))
    except Exception as e:
        log.error("Failed to link epic to a feature. Error: " + str(e))

def link_issues(jira, origin_issue, issues_and_links):
    ''' Links Jira <origin_issue> to the multiple issues from <issues_and_links>'''

    for destination_issue, link_type in issues_and_links.items():
        try:
            link_issue(jira, origin_issue, jira.issue(destination_issue), link_type)
        except Exception as e:
            log.error("Failed to link issue. Error: " + str(e))
