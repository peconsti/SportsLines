# Imports
import datetime
import traceback
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import utils
import queue
import smtplib

# EMAIL
# Addresses
fiba_predict_email_addresses = {1: {'1': 'sportslines@hotmail.com',
                                    '2': 'sportslines2@hotmail.com',
                                    '3': 'sportslines3@hotmail.com',
                                    '4': 'sportslines4@hotmail.com',
                                    '5': 'sportslines5@hotmail.com'},
                                2: {'1': 'sportslines6@hotmail.com',
                                    '2': 'sportslines7@hotmail.com',
                                    '3': 'sportslines8@hotmail.com',
                                    '4': 'sportslines9@hotmail.com',
                                    '5': 'sportslines10@hotmail.com'}}

# Passwords
fiba_predict_email_passwords = {1: {'1': 'lmzwjwmgoezggtzz',
                                    '2': 'ruajffbfbsxzalkn',
                                    '3': 'qkajxxlawccesttp',
                                    '4': 'lguunwgyptxuwfsf',
                                    '5': 'qubigilznzkbalrb'},
                                2: {'1': 'umikgklazohrfbja',
                                    '2': 'gdtxxzjcmrjfgkmy',
                                    '3': 'ujoppokoetqssnyz',
                                    '4': 'yjiupqzrftbhbqtw',
                                    '5': 'eomwxbudiwvalrfp'}}

# RECOVERY CODES
# 1 -> BLZEE-ZDYCD-4TCNY-NA37R-MZQ4K
# 2 -> WPABC-E3HL4-Z97CP-BY4UH-R8CK4
# 3 -> SH8QD-KV93A-NF94D-E2534-2S6XU
# 4 -> 4AJWP-TA3FY-X2DKQ-HH6LS-86U2V
# 5 -> 5GBYK-2JZYZ-BP72M-YZRT5-9YBAJ
# 6 -> 97LWH-TYVX6-5U6HZ-Y8TNZ-XU6YH
# 7 -> E2PT8-Y5TQN-EPAKC-F84P9-XV7FR
# 8 -> SE6CW-KBLPE-8MQZ2-X2U75-5TTUU
# 9 -> CUBBD-Z7MU5-P29MN-3JH44-5MR5E
# 10 -> W9AFZ-69Z8Y-3Q3UV-2TWH8-RQYCS


# Account schedule
email_account_schedule = {'1': '00:00-06:00',
                          '2': '06:00-12:00',
                          '3': '12:00-15:00',
                          '4': '15:00-18:00',
                          '5': '18:00-00:00'}

# New bet provider color
new_bet_provider_color = '#FCF47E'

# Centered stats
centered_stats = ['HC']

# HTML table width
html_table_width = 40  # percent

# Session files
mail_queue = queue.Queue()
send_later_queue = queue.Queue()
email_layer_to_use = [1]
schedule_id_to_use = ['1']
switch_layer = [False]


# Get email id to use
def get_email_id_to_use():
    # Schedule ID
    now = utils.get_datetime_now()
    sched_id_to_use = schedule_id_to_use[0]
    for email_id in email_account_schedule:
        lower_hour = datetime.datetime.strptime(email_account_schedule[email_id].split('-')[0], utils.alt_time_format)
        upper_hour = datetime.datetime.strptime(email_account_schedule[email_id].split('-')[1], utils.alt_time_format)
        if upper_hour < lower_hour:
            upper_hour = upper_hour.replace(year=now.year, month=now.month, day=now.day) + datetime.timedelta(days=1)
        else:
            upper_hour = upper_hour.replace(year=now.year, month=now.month, day=now.day)
        lower_hour = lower_hour.replace(year=now.year, month=now.month, day=now.day)
        if lower_hour < now < upper_hour:
            sched_id_to_use = email_id
            break

    # Update when schedule id changed
    if sched_id_to_use != schedule_id_to_use[0]:
        # Update schedule ID to use
        schedule_id_to_use[0] = sched_id_to_use

        # Reset layer when schedule ID changes
        email_layer_to_use[0] = 1

    # Layer
    if switch_layer[0]:
        if email_layer_to_use[0] == len(fiba_predict_email_addresses):
            email_layer_to_use[0] = 1
        else:
            email_layer_to_use[0] += 1

        switch_layer[0] = False


# Email
# Create connection
def create_conn():
    # Get layer and sched ID to use
    get_email_id_to_use()
    layer_to_use = email_layer_to_use[0]
    sched_id = schedule_id_to_use[0]

    # Create connection
    conn = smtplib.SMTP("smtp-mail.outlook.com", 587)  # creates SMTP session (HOTMAIL)
    conn.starttls()  # start TLS for security
    try:
        conn.login(fiba_predict_email_addresses[layer_to_use][sched_id],
                   fiba_predict_email_passwords[layer_to_use][sched_id])  # Authentication
    except smtplib.SMTPAuthenticationError:  # blocked account
        utils.print_to_console(fiba_predict_email_addresses[layer_to_use][sched_id] + ' is blocked?')
        switch_layer[0] = True
        conn = None

    return conn


email_conn = [create_conn()]


# TEST CONNECTION
def test_conn_open(conn):
    if conn is not None:
        try:
            status = conn.noop()[0]
        except smtplib.SMTPServerDisconnected:
            status = -1
    else:
        status = - 2  # no connection

    return True if status == 250 else False


def send_email(msg_tuple):
    # Test connection
    if not test_conn_open(email_conn[0]) or switch_layer[0]:  # if switch email
        email_conn[0] = create_conn()

    # Get email address to use
    sched_id = schedule_id_to_use[0]
    layer = email_layer_to_use[0]
    email_address_to_use = fiba_predict_email_addresses[layer][sched_id]
    msg_to_use = msg_tuple[0][layer][sched_id]

    # Get account id to use
    if email_conn[0] is not None:
        # Send
        try:
            email_conn[0].sendmail(email_address_to_use, msg_tuple[1], msg_to_use.as_string())
            utils.print_to_console('Sent email: ' + msg_to_use['Subject'] + ' ' + str(msg_tuple[1]) + ' [' +
                                   msg_tuple[2] + ']' + ' Sender: ' + email_address_to_use +
                                   ' [' + str(layer) + ', ' + sched_id + ']')
        except smtplib.SMTPDataError:
            utils.print_to_console('Email was considered spam: ' + msg_to_use['Subject'] + ' ' + str(msg_tuple[1]) +
                                   ' [' + msg_tuple[2] + ']' + ' Sender: ' + email_address_to_use +
                                   ' [' + str(layer) + ', ' + sched_id + ']')
            traceback.print_exc()

            send_later_queue.put(msg_tuple)
            switch_layer[0] = True
        except smtplib.SMTPSenderRefused:
            utils.print_to_console('Email not sent because sender refused: ' +
                                   msg_to_use['Subject'] + ' ' + str(msg_tuple[1]) + ' [' + msg_tuple[2] + '] ' +
                                   ' [' + str(layer) + ', ' + sched_id + ']')
            send_later_queue.put(msg_tuple)
        except smtplib.SMTPRecipientsRefused:
            utils.print_to_console('Email not sent because recipients refused: ' +
                                   msg_to_use['Subject'] + ' ' + str(msg_tuple[1]) + ' [' + msg_tuple[2] + '] ' +
                                   ' [' + str(layer) + ', ' + sched_id + ']')
            send_later_queue.put(msg_tuple)
    else:
        utils.print_to_console(email_address_to_use + ' is locked?: ' + msg_to_use['Subject'] + ' ' +
                               str(msg_tuple[1]) + ' [' + msg_tuple[2] + ']' +
                               ' [' + str(layer) + ', ' + sched_id + ']')
        send_later_queue.put(msg_tuple)


# CREATE REPORT
def create_report(report_type, bet_sheet, extra_var):
    # Teams
    h_name = bet_sheet['Home']
    a_name = bet_sheet['Away']

    # Datetime
    game_datetime = bet_sheet['Datetime']

    # HEADER
    html_header = h_name + ' vs. ' + a_name

    # Links ToDo remove
    links = [bet_sheet['Link']]

    # ODDS
    betting_odds = {}
    for b_prov in bet_sheet['BettingOdds']:
        betting_odds[b_prov] = {}
        for bet_mom in bet_sheet['BettingOdds'][b_prov]:
            if bet_mom == 'Kickoff' and not bet_sheet['Started']:
                continue

            betting_odds[b_prov][bet_mom] = bet_sheet['BettingOdds'][b_prov][bet_mom]

    # MAIL
    send_to = get_send_report_to(bet_sheet['League'], report_type)
    send_to_incognito = [e_address.replace(' [I]', '') for e_address in send_to if ' [I]' in e_address]
    send_to_clear = [e_address for e_address in send_to if ' [I]' not in e_address]

    # SEND CLEAR
    for send_to in [('Clear', send_to_clear), ('Inc.', send_to_incognito)]:
        if report_type not in ['Bet open', 'New bet open'] and send_to[0] == 'Inc.':
            continue

        if send_to[1]:
            # Subject
            subject_content = '[' + bet_sheet['League'] + '] ' + ' (' + h_name + ' vs. ' + a_name + ') ' + \
                              report_type + 'ed' + ' (' + game_datetime + ')'

            # Body
            if send_to[0] == 'Clear':
                html_body_of_email = generate_html_report(html_header, links, betting_odds, extra_var)
            else:
                html_body_of_email = generate_incognito_html_report(html_header, betting_odds, extra_var)

            alt_messages = {}
            for layer_num in fiba_predict_email_addresses:
                for sched_id in fiba_predict_email_addresses[layer_num]:
                    msg = MIMEMultipart()
                    msg['From'] = fiba_predict_email_addresses[layer_num][sched_id]
                    msg['Cc'] = fiba_predict_email_addresses[layer_num][sched_id]
                    msg['Subject'] = subject_content

                    part2 = MIMEText(html_body_of_email, 'html')
                    msg.attach(part2)

                    if layer_num not in alt_messages:
                        alt_messages[layer_num] = {}

                    alt_messages[layer_num][sched_id] = msg

            mail_queue.put((alt_messages, send_to[1], send_to[0]))


# Generate odds HTML table
def odds_html_table(betting_odds, extra_var):
    odds_html_string = """"""

    if betting_odds:
        # Start
        odds_html_string += """
                    <p>
                    <table style="width:""" + str(html_table_width) + """%">"""

        # Headers
        headers = ['Provider', 'Mom.', 'HC', 'HC H', 'HC A', 'HC time', 'WIN H', 'WIN A', 'WIN time']

        odds_html_string += """<tr>"""
        for h_title in headers:
            odds_html_string += """<th>""" + h_title + """</th>"""
        odds_html_string += """</tr>"""

        # Lines
        for b_prov in betting_odds:
            num_times = 0
            for bet_mom in betting_odds[b_prov]:
                if betting_odds[b_prov][bet_mom]['hc_timestamp'] is not None or \
                        betting_odds[b_prov][bet_mom]['win_timestamp'] is not None:
                    num_times += 1

            if num_times > 0:
                odds_html_string += """<tr>"""
                b_prov_string = b_prov
                if extra_var is not None and b_prov in extra_var:
                    b_prov_string = """<span style="background-color: """ + \
                                    new_bet_provider_color + """;">""" + b_prov + """</span>"""

                odds_html_string += """<td rowspan = """ + '"' + str(num_times) + '"' + """> """ + \
                                    b_prov_string + """</td>"""

                line_num = 1
                for bet_mom in betting_odds[b_prov]:
                    if betting_odds[b_prov][bet_mom]['hc_timestamp'] is not None or \
                            betting_odds[b_prov][bet_mom]['win_timestamp'] is not None:
                        if line_num != 1:
                            odds_html_string += """<tr>"""

                        # Time
                        odds_html_string += """<td>""" + bet_mom + """</td>"""

                        # HC
                        odds_html_string += """<td>""" + \
                                            utils.get_hc_string(betting_odds[b_prov][bet_mom]['home_hc']) + """</td>"""

                        # Home HC odd
                        odds_html_string += """<td>""" + utils.get_odd_string(
                            betting_odds[b_prov][bet_mom]['home_hc_odd']) + """</td>"""

                        # Home HC odd
                        odds_html_string += """<td>""" + utils.get_odd_string(
                            betting_odds[b_prov][bet_mom]['away_hc_odd']) + """</td>"""

                        # HC timestamp
                        hc_timestamp = betting_odds[b_prov][bet_mom]['hc_timestamp']
                        if hc_timestamp is not None:
                            hc_timestamp = utils.conv_odd_timestamp_to_str(hc_timestamp)
                        else:
                            hc_timestamp = ''
                        odds_html_string += """<td>""" + hc_timestamp + """</td>"""

                        # Home win odd
                        odds_html_string += """<td>""" + utils.get_odd_string(
                            betting_odds[b_prov][bet_mom]['home_w_odd']) + """</td>"""

                        # Away win odd
                        odds_html_string += """<td>""" + utils.get_odd_string(
                            betting_odds[b_prov][bet_mom]['away_w_odd']) + """</td>"""

                        # WIN timestamp
                        win_timestamp = betting_odds[b_prov][bet_mom]['win_timestamp']
                        if win_timestamp is not None:
                            win_timestamp = utils.conv_odd_timestamp_to_str(win_timestamp)
                        else:
                            win_timestamp = ''
                        odds_html_string += """<td>""" + win_timestamp + """</td>"""

                        odds_html_string += """</tr>"""

                    line_num += 1

        # End
        odds_html_string += """</table>
            </p>"""

    return odds_html_string


# Generate incognito HTML report
def generate_incognito_html_report(header, betting_odds, extra_var):
    html_string = """\
    <html>
    <head>
    <style>
    td, th {
      white-space: nowrap;
      overflow: hidden;
    }
    tr:hover {background-color: #D6EEEE;}
    </style>
    </head>
    <body>"""

    # Header
    html_string += """<h2>""" + header + """</h2>"""

    # Betting odds
    if betting_odds:
        html_string += """<h3>""" + """Odds""" + """</h3>"""
        html_string += odds_html_table(betting_odds, extra_var)

    html_string += """
      </body>
    </html>
    """

    return html_string


# Generate HTML report
def generate_html_report(header, links, betting_odds, extra_var):
    html_string = """\
<html>
<head>
<style>
td, th {
  white-space: nowrap;
  overflow: hidden;
}
tr:hover {background-color: #D6EEEE;}
</style>
</head>
<body>"""

    # Header
    html_string += """<h2>""" + header + """</h2>"""

    # Links
    html_string += """<p>""" + links[0] + """</p>"""

    # Betting odds
    if betting_odds:
        html_string += """<h3>""" + """Odds""" + """</h3>"""
        html_string += odds_html_table(betting_odds, extra_var)

    html_string += """
  </body>
</html>
"""

    return html_string


# Get send report to
def get_send_report_to(l_name, bet_providers):
    send_to = []
    prov_codes = [utils.bet_providers[b_prov] for b_prov in utils.bet_providers if b_prov in bet_providers]
    for username in utils.reports_config:
        send_to_him = False

        # All FIBA IDs
        if 'All' in utils.reports_config[username]['alerts'] and \
                (any(i in prov_codes for i in utils.reports_config[username]['alerts']['All']) or
                 'All' in utils.reports_config[username]['alerts']['All']):
            send_to_him = True

        # One league
        if l_name in utils.reports_config[username]['alerts'] and \
                (any(i in prov_codes for i in utils.reports_config[username]['alerts'][l_name]) or
                 'All' in utils.reports_config[username]['alerts'][l_name]):
            send_to_him = True

        # Incognito
        if send_to_him:
            if ' [I]' in username:
                send_to.append(utils.reports_config[username]['email'] + ' [I]')
            else:
                send_to.append(utils.reports_config[username]['email'])

    return send_to
