# Imports
import datetime

# Config folder path
config_folder_path = '.\\config'

# Bet providers path
bet_providers_filename = 'bet_providers.txt'
bet_providers_filepath = config_folder_path + '\\' + bet_providers_filename

# League coverage path
league_coverage_filename = 'league_coverage.txt'
league_coverage_filepath = config_folder_path + '\\' + league_coverage_filename

# Reports
reports_config_filename = 'reports_config.txt'
reports_config_filepath = config_folder_path + '\\' + reports_config_filename

# Year time
year_time = 'winter'

# Time formats
conv_odd_date_format = '%d/%m %H:%M'
conv_schedule_format = '%d/%m/%y %H:%M'
file_name_timestamp_format = '%d-%m-%y-%H-%M-%S'
alt_time_format = '%H:%M'

# Session files
bet_providers = {}
league_coverage = {}
reports_config = {}


# Get date time now
def get_datetime_now():
    if year_time == 'winter':
        return datetime.datetime.utcnow()
    else:
        return datetime.datetime.utcnow() + datetime.timedelta(hours=1)


# Print to console
def print_to_console(string):
    print('[' + str(get_datetime_now())[:-4] + '] ' + string)


# Convert odd timestamp to string
def conv_odd_timestamp_to_str(odd_timestamp):
    return odd_timestamp.strftime(conv_odd_date_format)


# Unix epoch to datetime
def unix_timestamp_to_datetime(event_time):
    if year_time == 'winter':
        return datetime.datetime.utcfromtimestamp(int(event_time))
    else:
        return datetime.datetime.utcfromtimestamp(int(event_time)) + datetime.timedelta(hours=1)


# Get hc string
def get_hc_string(hc_value):
    hc_value_to_print = ''
    if hc_value is not None:
        hc_value = round(hc_value, 1)
        hc_value_to_print = str(hc_value)

        if '-' not in hc_value_to_print and hc_value != 0:
            hc_value_to_print = '+' + hc_value_to_print

    return hc_value_to_print


# Get odd string
def get_odd_string(odd_value):
    if odd_value is not None:
        return str(round(odd_value, 2))
    else:
        return ''


# Import bet providers
def import_bet_providers():
    try:
        with open(bet_providers_filepath, encoding='utf8') as f:
            lines = [line[:-1] for line in f.readlines()]
        print_to_console('Imported ' + bet_providers_filepath)
    except FileNotFoundError:
        print_to_console(bet_providers_filepath + ' not found')
    except PermissionError:
        print_to_console(bet_providers_filepath + ' is being used')
    except OSError:
        print_to_console('Error opening ' + bet_providers_filepath)
    else:
        # Clean
        bet_providers.clear()

        for line in lines:
            if line == '' or line == '\n' or line[1] == '#':
                continue

            prov_name = line.split(': ')[0]
            prov_code = line.split(': ')[1]
            bet_providers[prov_name] = prov_code

    return bet_providers


# Import league coverage
def import_league_coverage():
    try:
        with open(league_coverage_filepath, encoding='utf8') as f:
            lines = [line[:-1] for line in f.readlines()]
        print_to_console('Imported ' + league_coverage_filepath)
    except FileNotFoundError:
        print_to_console(league_coverage_filepath + ' not found')
    except PermissionError:
        print_to_console(league_coverage_filepath + ' is being used')
    except OSError:
        print_to_console('Error opening ' + league_coverage_filepath)
    else:
        # Clean
        league_coverage.clear()

        for line in lines:
            if line == '' or line == '\n' or line[0] == '#':
                continue

            league_name = line.split(': ')[0]
            days_ahead = float(line.split(': ')[1])
            league_coverage[league_name] = days_ahead

    return league_coverage


# Alerts config import
def import_reports_config():
    try:
        with open(reports_config_filepath, encoding='utf8') as f:
            lines = [line[:-1] for line in f.readlines()]
        print_to_console('Imported ' + reports_config_filepath)
    except FileNotFoundError:
        print_to_console(reports_config_filepath + ' not found')
    except PermissionError:
        print_to_console(reports_config_filepath + ' is being used')
    except OSError:
        print_to_console('Error opening ' + reports_config_filepath)
    else:
        # Clean
        reports_config.clear()

        # Get
        last_line_idx = len(lines)
        user_borders = [(lines[l_idx][1:], l_idx) for l_idx in range(len(lines)) if
                        lines[l_idx] and lines[l_idx][0] == '@']
        num_users = len(user_borders)
        for user_idx in range(num_users):
            # Collect email
            email = lines[user_borders[user_idx][1] + 1].strip()

            # Collect alert matrix
            start_matrix = user_borders[user_idx][1] + 2
            if user_idx == num_users - 1:
                stop_matrix = last_line_idx
            else:
                stop_matrix = user_borders[user_idx + 1][1]
            alerts_matrix = {}
            for l_idx in range(start_matrix, stop_matrix):
                if lines[l_idx] != '\n' and lines[l_idx] != '':
                    l_split = lines[l_idx].strip().split(':')
                    league_name = l_split[0]
                    alert_types = [a_type for a_type in l_split[1].split(',')]

                    if league_name not in alerts_matrix:
                        alerts_matrix[league_name] = {}

                    alerts_matrix[league_name] = alert_types

            # Save
            user_name = user_borders[user_idx][0].strip()
            reports_config[user_name] = {'email': email,
                                         'alerts': alerts_matrix}


# Refresh config
def refresh_config():
    print_to_console('### Importing config')
    import_bet_providers()
    import_league_coverage()
    import_reports_config()
    print('')


refresh_config()
