# Imports
import http.client
import os
from datetime import datetime, timedelta
import zipfile
import math
import requests
import utils
import pandas as pd
import json
import time

# I/O
to_replace = 'XXXXX'
bet_folder_path = '.\\bet_schedule'
bet_schedule_pref = 'bet_schedule_'
bet_schedule_filepath_template = bet_folder_path + '\\' + bet_schedule_pref + 'XXXXX.xlsx'

# Request info
# Credentials
our_token = '124191-1hb7LMTKumwl1E'
sport_id = '18'

# Schedule
upcoming_request_link = 'https://api.b365api.com/v3/events/upcoming?sport_id=' + sport_id + '&token=' + our_token
in_play_request_link = 'https://api.b365api.com/v3/events/inplay?sport_id=' + sport_id + '&token=' + our_token
max_num_event_pages = 40

# Event odds
odds_summary_request_link = 'https://api.b365api.com/v2/event/odds/summary?token=' + our_token + '&event_id='
odds_summary_link_template = 'https://pt.betsapi.com/rs/'

# Bet providers
bet_providers = list(utils.bet_providers.keys())

# Bet schedule
bet_schedule_headers = ['Datetime', 'League', 'Home', 'Away', 'Link', 'EventID', 'Started']
max_num_schedule_files = 10

# Betting odds variables
betting_moments = ['Line',
                   'Kickoff',
                   'Live']

# Bet moment to betsapi convention
bet_mom_to_betsapi = {'Line': 'start',
                      'Kickoff': 'kickoff',
                      'Live': 'end'}

# Betting variables ToDo under/over?
bet_vars = ['home_w_odd',
            'away_w_odd',
            'home_hc',
            'home_hc_odd',
            'away_hc_odd',
            'win_timestamp',
            'hc_timestamp']

# NCAA leagues
ncaa_leagues = ['NCAAB', 'WNCAAB']

# Swap leagues
swap_leagues = ncaa_leagues

# Swap HC providers
swap_hc_providers = ['Bet365', '1XBet', 'PinnacleSports']

# Refresh times
bet_sched_refresh_time = 1 * 60  # seconds

# Session files
bet_sched = {}
last_b_sched_time = [utils.get_datetime_now() - timedelta(seconds=bet_sched_refresh_time)]


# LINKS
# URLize name
def urlize_name_alt(name):
    name = name.replace('(', '%28').replace(')', '%29').replace(' ', '-').replace('/', '-')
    return name


# Generate odds summary request link
def generate_odds_summary_request_link(game_id):
    return odds_summary_request_link + game_id


# Generate bet api link
def generate_odds_summary_link(bet_event):
    bet_home_name = bet_event['home']['name']
    if 'o_home' in bet_event:
        bet_home_name = bet_event['o_home']['name']
    bet_away_name = bet_event['away']['name']
    if 'o_away' in bet_event:
        bet_away_name = bet_event['o_away']['name']
    home_name = urlize_name_alt(bet_home_name)
    away_name = urlize_name_alt(bet_away_name)

    return odds_summary_link_template + bet_event['id'] + '/' + home_name + '-vs-' + away_name


# BET SCHEDULE
# Get bet schedule file names
def get_bet_schedule_file_names():
    all_files = []

    try:
        all_files = os.listdir(bet_folder_path)
    except FileNotFoundError:
        """Do nothing"""
    else:
        all_files = [file for file in all_files if bet_schedule_pref in file and '~$' not in file]

        # Sort per date
        all_files = sorted(all_files,
                           key=lambda x: datetime.strptime(x.replace(bet_schedule_pref, '').replace('.xlsx', ''),
                                                           utils.file_name_timestamp_format), reverse=True)

    return all_files


# Import bet schedule
def import_bet_schedule(filepath):
    bet_events = {}

    try:
        bet_events = pd.read_excel(filepath, engine='openpyxl').set_index('Link').T.to_dict('dict')
        utils.print_to_console('Imported ' + filepath + '\n')
    except FileNotFoundError:
        utils.print_to_console('File not found: ' + filepath)
    except PermissionError:
        utils.print_to_console(filepath + ' is being used')
    except OSError:
        utils.print_to_console('Invalid argument importing bet schedule: ' + filepath)
    except zipfile.BadZipfile:
        utils.print_to_console('Could not import bet schedule: ' + filepath)

    return bet_events


# Import current bet schedule
def import_current_bet_schedule():
    bet_schedule = {}

    bet_schedule_files = get_bet_schedule_file_names()
    if len(bet_schedule_files) > 0:
        # Get most recent file
        path_to_import = bet_folder_path + '\\' + bet_schedule_files[0]

        # Import
        bet_schedule = import_bet_schedule(path_to_import)

    return bet_schedule


# Refresh bet schedule
def refresh_bet_sched():
    time_now = utils.get_datetime_now()
    if (time_now - last_b_sched_time[0]).total_seconds() > bet_sched_refresh_time:
        bet_sched_aux = import_current_bet_schedule()
        if bet_sched_aux:
            last_b_sched_time[0] = time_now
            bet_sched.clear()
            for bet_link in bet_sched_aux:
                event_id = str(bet_sched_aux[bet_link]['EventID'])
                bet_sched[event_id] = {'Link': bet_link} | bet_sched_aux[bet_link]


# REQUEST EVENT ODDS
# Normalize odd
def normalize_odd(odd):
    if odd in ['-', '']:
        return float(1)
    else:
        try:
            return float(odd)
        except TypeError:
            return None


# Request event odds
def request_event_odds(bet_link, l_name=None, timeout=None):
    # Collect odds
    betting_odds = {}
    event_id_not_found = False
    time_elapsed = None
    timed_out = False

    # Request
    start_time = time.time()
    try:
        if timeout is None:  # 60 seconds time out
            timeout = 60
        result = requests.get(url=bet_link, verify=False, timeout=timeout).json()
        time_elapsed = time.time() - start_time
    except json.decoder.JSONDecodeError:
        utils.print_to_console('Can not request: ' + bet_link)
    except requests.exceptions.ConnectionError:
        timed_out = True
        utils.print_to_console('Connection error: ' + bet_link)
    except http.client.RemoteDisconnected:
        timed_out = True
        utils.print_to_console('Remote disconnection: ' + bet_link)
    except requests.exceptions.ReadTimeout:
        timed_out = True
        time_elapsed = time.time() - start_time
    # print("--- %s seconds ---" % (time.time() - start_time))
    else:
        if 'results' in result and result['results']:
            for provider in bet_providers:
                if provider in result['results']:
                    template = {bet_mom: {var: None for var in bet_vars} for bet_mom in betting_moments}
                    betting_odds[provider] = {bet_mom: {var: None for var in bet_vars} for bet_mom in betting_moments}
                    for bet_moment in betting_moments:
                        # Get betsapi convention
                        betsapi_mom_conv = bet_mom_to_betsapi[bet_moment]

                        if betsapi_mom_conv not in result['results'][provider]['odds']:
                            continue

                        # Get odds summary
                        odds_summary = result['results'][provider]['odds'][betsapi_mom_conv]

                        # Win
                        if odds_summary['18_1'] is not None:
                            betting_odds[provider][bet_moment]['home_w_odd'] = \
                                normalize_odd(odds_summary['18_1']['home_od'])
                            betting_odds[provider][bet_moment]['away_w_odd'] = \
                                normalize_odd(odds_summary['18_1']['away_od'])

                            betting_odds[provider][bet_moment]['win_timestamp'] = \
                                utils.unix_timestamp_to_datetime(result['results'][provider]['odds'][
                                                                     betsapi_mom_conv]['18_1']['add_time'])

                        # HC
                        if odds_summary['18_2'] is not None and odds_summary['18_2']['handicap'] != '':
                            betting_odds[provider][bet_moment]['home_hc'] = \
                                float(odds_summary['18_2']['handicap'])
                            betting_odds[provider][bet_moment]['home_hc_odd'] = \
                                normalize_odd(odds_summary['18_2']['home_od'])
                            betting_odds[provider][bet_moment]['away_hc_odd'] = \
                                normalize_odd(odds_summary['18_2']['away_od'])

                            betting_odds[provider][bet_moment]['hc_timestamp'] = \
                                utils.unix_timestamp_to_datetime(result['results'][provider]['odds'][
                                                                     betsapi_mom_conv]['18_2']['add_time'])

                        # Correct PinnacleSports HCs (only if win odds are available and are different)
                        if provider == 'PinnacleSports':
                            if betting_odds[provider][bet_moment]['home_hc'] is not None:
                                if betting_odds[provider][bet_moment]['home_w_odd'] is not None and \
                                        betting_odds[provider][bet_moment]['away_w_odd'] is not None:
                                    hc_signal = math.copysign(1, betting_odds[provider][bet_moment]['home_hc'])
                                    if betting_odds[provider][bet_moment]['home_w_odd'] < \
                                            betting_odds[provider][bet_moment]['away_w_odd']:
                                        if hc_signal == 1:
                                            betting_odds[provider][bet_moment]['home_hc'] = - \
                                                betting_odds[provider][bet_moment]['home_hc']
                                    elif betting_odds[provider][bet_moment]['home_w_odd'] > \
                                            betting_odds[provider][bet_moment]['away_w_odd']:
                                        if hc_signal == -1:
                                            betting_odds[provider][bet_moment]['home_hc'] = - \
                                                betting_odds[provider][bet_moment]['home_hc']

                        # Swap odds for selected leagues ToDo?
                        if l_name in swap_leagues:
                            # HC
                            if provider not in swap_hc_providers:
                                if betting_odds[provider][bet_moment]['home_hc'] is not None:
                                    betting_odds[provider][bet_moment]['home_hc'] = \
                                        -betting_odds[provider][bet_moment]['home_hc']

                    # Delete if empty
                    if betting_odds[provider] == template:
                        del betting_odds[provider]

        elif 'error' in result:
            if result['error'] == 'PARAM_INVALID' and 'error_detail' in result and \
                    result['error_detail'] == 'event_id':  # bet event ID changed
                event_id_not_found = True
            else:
                detail = ''
                if 'error_detail' in result:
                    detail = result['error_detail']
                utils.print_to_console('BetsAPI: ' + result['error'] + ': ' + detail + ' (' + bet_link + ') ')
                timed_out = True

    return betting_odds, event_id_not_found, time_elapsed, timed_out
