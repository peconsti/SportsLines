# Imports
import utils
import bet_func
import report
from urllib3 import disable_warnings, exceptions
from PyInstaller.utils.hooks import collect_data_files
from threading import Thread
import time
import datetime

# Burocracy
disable_warnings(exceptions.InsecureRequestWarning)
collect_data_files('certifi')

# Maximum times a bet event can be unseen (consecutive)
max_times_unseen = 10 * (250 / 5)

# Refresh times
auto_config_time = 5 * 60  # seconds

# Session files
bet_links_opened = {}
bet_links_opened_info = {}
bet_links_to_open_check = {}
new_bet_links_open_check = {}
num_times_unseen = {}
bet_open_start = [utils.get_datetime_now()]
new_bet_open_start = [utils.get_datetime_now()]
last_config_time = [utils.get_datetime_now()]
num_new_bet_open = [0]
num_bet_matcher_rounds = [0]
first_bet_matcher = [False]


# Clear emails
def clear_emails():
    with report.mail_queue.mutex:
        report.mail_queue.queue.clear()


# Send emails
def send_emails():
    # Send later
    while not report.send_later_queue.empty():
        msg_tuple = report.send_later_queue.get()
        report.send_email(msg_tuple)

    # Mail queue
    while not report.mail_queue.empty():
        msg_tuple = report.mail_queue.get()
        report.send_email(msg_tuple)


# Game matcher
def bet_open():
    while True:
        # Refresh bet schedule
        bet_func.refresh_bet_sched()

        # Start
        if all(item is False for item in bet_links_to_open_check.values()):
            utils.print_to_console('### Bet open started')
            bet_open_start[0] = utils.get_datetime_now()

        event_num = 0
        # num_events = len(bet_func.bet_sched)
        now = utils.get_datetime_now()
        for event_id in bet_func.bet_sched:
            event_num += 1

            # Skip non-covered leagues
            bet_league = bet_func.bet_sched[event_id]['League']
            if bet_league not in utils.league_coverage:
                continue

            # Skip games that are too early too check
            game_date = datetime.datetime.strptime(bet_func.bet_sched[event_id]['Datetime'], utils.conv_schedule_format)
            diff_in_days = (game_date - now).total_seconds() / (60 * 60 * 24)
            if diff_in_days > utils.league_coverage[bet_league]:
                continue

            # Skip bet links already opened
            if event_id in bet_links_opened:
                continue

            # Skip bet links to open already checked
            if event_id in bet_links_to_open_check and bet_links_to_open_check[event_id]:
                continue

            # Info
            home = bet_func.bet_sched[event_id]['Home']
            away = bet_func.bet_sched[event_id]['Away']
            date = bet_func.bet_sched[event_id]['Datetime']
            bet_link = bet_func.bet_sched[event_id]['Link']

            # Bet open report
            req_link = bet_func.generate_odds_summary_request_link(event_id)
            betting_odds, _, time_elapsed, timed_out = bet_func.request_event_odds(req_link, bet_league)
            if time_elapsed is not None:
                time_elapsed = round(time_elapsed, 2)

            # Skip not opened (or timed out)
            if not timed_out:
                # utils.print_to_console('Checking bet open: ' + event_id + ' (' + home + ' vs. ' + away + ') ' +
                #                        date + ' ' + bet_link + ' [' + str(event_num) + '/' + str(num_events) + ']' +
                #                        ' [' + str(time_elapsed) + ']')

                if betting_odds:
                    providers = list(betting_odds.keys())

                    # Add to bet links opened
                    bet_links_opened[event_id] = providers
                    bet_links_opened_info[event_id] = bet_func.bet_sched[event_id]

                    send_to = report.get_send_report_to(bet_league, providers)

                    utils.print_to_console('Bet opened: ' + home + ' vs. ' + away +
                                           ' (' + date + ')' + ' (' + bet_link + ') ' +
                                           str(providers) + ' [' + str(round(time_elapsed, 2)) + 's]')

                    # SEND EMAIL
                    if send_to:
                        # Create report
                        bet_sheet = bet_func.bet_sched[event_id] | {'BettingOdds': betting_odds}
                        report.create_report('Bet open', bet_sheet, None)
                else:
                    bet_links_to_open_check[event_id] = True
            else:
                utils.print_to_console('Bet open timed out: ' + event_id + ' (' + home + ' vs. ' + away + ') ' +
                                       date + ' ' + bet_link)
                bet_links_to_open_check[event_id] = False
                continue

        # Clean
        # Bet links opened
        opened_to_remove = []
        for event_id in bet_links_opened:
            if event_id not in bet_func.bet_sched:
                if event_id not in num_times_unseen:
                    num_times_unseen[event_id] = 0
                num_times_unseen[event_id] += 1
                if num_times_unseen[event_id] > max_times_unseen:
                    opened_to_remove.append(event_id)
            else:
                # Reset number of times unseen
                if event_id in num_times_unseen:
                    del num_times_unseen[event_id]

        for event_id in opened_to_remove:
            utils.print_to_console('Removed bet link open: ' + event_id)
            del bet_links_opened[event_id]
            del bet_links_opened_info[event_id]
            del num_times_unseen[event_id]

        # Bet links to open
        to_open_to_remove = []
        for event_id in bet_links_to_open_check:
            if event_id not in bet_func.bet_sched or event_id in bet_links_opened:
                to_open_to_remove.append(event_id)
                if event_id in bet_links_opened:
                    utils.print_to_console('Removed bet event to open: ' + event_id)

        for event_id in to_open_to_remove:
            del bet_links_to_open_check[event_id]

        # Reset check
        if all(bet_links_to_open_check.values()):
            # Summary
            total_time_elapsed = round((utils.get_datetime_now() - bet_open_start[0]).total_seconds() / 60, 2)
            utils.print_to_console('Number of bet links opened = ' + str(len(bet_links_opened)))
            utils.print_to_console('Number of bet links to open = ' + str(len(bet_links_to_open_check)))
            utils.print_to_console('Total number events in schedule = ' + str(len(bet_func.bet_sched)))
            utils.print_to_console('Total time elapsed = ' + str(total_time_elapsed) + 'min')
            utils.print_to_console('Done' + '\n')

            # Reset bet links to open check
            for event_id in bet_links_to_open_check:
                bet_links_to_open_check[event_id] = False

            num_bet_matcher_rounds[0] += 1

        time.sleep(1)


# New bet open
def new_bet_open():
    while True:
        if first_bet_matcher[0]:
            bet_links_open_aux = dict(bet_links_opened)
            bet_links_open_info_aux = dict(bet_links_opened_info)

            if bet_links_open_aux:
                # Start
                if not new_bet_links_open_check or all(item is False for item in new_bet_links_open_check.values()):
                    utils.print_to_console('### New bet open started')
                    new_bet_open_start[0] = utils.get_datetime_now()

                # Check opened events
                event_num = 0
                # num_events = len(bet_links_open_aux)
                for event_id in bet_links_open_aux:
                    event_num += 1
                    bet_link = bet_links_open_info_aux[event_id]['Link']

                    if event_id in new_bet_links_open_check and new_bet_links_open_check[event_id]:
                        # skip checked links
                        continue

                    req_link = bet_func.generate_odds_summary_request_link(event_id)
                    league_name = bet_links_open_info_aux[event_id]['League']
                    betting_odds, _, time_elapsed, timed_out = bet_func.request_event_odds(req_link, league_name,
                                                                                           timeout=3)
                    if time_elapsed is not None:
                        time_elapsed = round(time_elapsed, 2)

                    if timed_out:
                        utils.print_to_console('New bet opened timed out: ' + bet_link + ' [' +
                                               str(time_elapsed) + 's]')
                        continue
                    # else:
                    #     utils.print_to_console('Checking new bet open: ' + bet_link + ' [' + str(event_num) + '/' +
                    #                            str(num_events) + ']' + ' [' + str(time_elapsed) + ']')

                    if betting_odds:
                        date = bet_links_open_info_aux[event_id]['Datetime']
                        new_providers = []
                        is_new_providers = False
                        for provider in betting_odds:
                            if provider not in bet_links_open_aux[event_id]:
                                new_providers.append(provider)
                                is_new_providers = True

                        if new_providers and is_new_providers:
                            bet_links_open_aux[event_id] += new_providers
                            h_match_name = bet_links_open_info_aux[event_id]['Home']
                            a_match_name = bet_links_open_info_aux[event_id]['Away']

                            utils.print_to_console('New bet opened: ' + h_match_name + ' vs. ' + a_match_name +
                                                   ' (' + date + ')' + ' (' + bet_link + ') ' +
                                                   str(new_providers) + ' [' + str(round(time_elapsed, 2)) + 's]')

                            send_to = report.get_send_report_to(league_name, 'New bet open')

                            # SEND EMAIL
                            if send_to:
                                # New bet open alert
                                bet_sheet = bet_func.bet_sched[event_id] | {'BettingOdds': betting_odds}
                                report.create_report('New bet open', bet_sheet, new_providers)

                                num_new_bet_open[0] += 1

                    new_bet_links_open_check[event_id] = True

                # Clean
                # Bet links opened check
                new_bet_to_remove = []
                for event_id in new_bet_links_open_check:
                    if event_id not in bet_links_open_aux:
                        new_bet_to_remove.append(event_id)

                for event_id in new_bet_to_remove:
                    del new_bet_links_open_check[event_id]
                    utils.print_to_console('Removed event from new bet: ' + event_id)

                # Reset
                if all(new_bet_links_open_check.values()) and len(new_bet_links_open_check) == len(bet_links_open_aux):
                    # Reset bet open checked
                    for event_id in new_bet_links_open_check:
                        new_bet_links_open_check[event_id] = False

                    # Summary
                    total_time_elapsed = round((utils.get_datetime_now() - new_bet_open_start[0]).total_seconds() / 60,
                                               2)
                    utils.print_to_console('Number of new bet open = ' + str(num_new_bet_open[0]))
                    utils.print_to_console('Total number of bet open = ' + str(len(bet_links_open_aux)))
                    utils.print_to_console('Total time elapsed = ' + str(total_time_elapsed) + 'min')
                    utils.print_to_console('Done' + '\n')

                    # Reset number of new bet open
                    num_new_bet_open[0] = 0  # reset number of new bets open

        time.sleep(1)


# Start message
utils.print_to_console('###  SportsLine service started')

# Bet open thread
t1 = Thread(target=bet_open)
t1.start()

# New bet open thread
t2 = Thread(target=new_bet_open)
t2.start()

# Main loop
while True:
    # Refresh config
    time_now = utils.get_datetime_now()
    if (time_now - last_config_time[0]).total_seconds() > auto_config_time:
        last_config_time[0] = time_now
        utils.refresh_config()

    # Send emails
    if num_bet_matcher_rounds[0] > 0:
        if not first_bet_matcher[0]:
            clear_emails()
            first_bet_matcher[0] = True
        send_emails()
    else:
        clear_emails()

    time.sleep(1)
