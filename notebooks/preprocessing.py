import numpy as np
import pandas as pd
import multiprocessing
from multiprocessing import Pool

from utils.preprocessing import one_hot_encoding
from utils.preprocessing import get_weekday


def process_user_session(user):
    user_session = sessions.loc[sessions['user_id'] == user]
    # Get the user session
    user_session_data = pd.Series()

    # Length of the session
    user_session_data['session_lenght'] = len(user_session)
    user_session_data['id'] = user

    suffix = '_secs_elapsed'

    for column in ['action', 'action_type', 'action_detail', 'device_type']:
        column_data = user_session.groupby(column).secs_elapsed.sum()
        column_data.rename(lambda x: x + suffix, inplace=True)
        user_session_data = user_session_data.append(column_data)

    # Get the most used device
    user_session_data['most_used_device'] = user_session['device_type'].max()

    return user_session_data.groupby(level=0).sum()


def process_user_secs_elapsed(user):
    user_secs = sessions.loc[sessions['user_id'] == user, 'secs_elapsed']
    user_processed_secs = pd.Series()
    user_processed_secs['id'] = user

    user_processed_secs['secs_elapsed_sum'] = user_secs.sum()
    user_processed_secs['secs_elapsed_mean'] = user_secs.mean()
    user_processed_secs['secs_elapsed_min'] = user_secs.min()
    user_processed_secs['secs_elapsed_max'] = user_secs.max()
    user_processed_secs['secs_elapsed_quantile_1'] = user_secs.quantile(0.25)
    user_processed_secs['secs_elapsed_quantile_3'] = user_secs.quantile(0.75)
    user_processed_secs['secs_elapsed_median'] = user_secs.median()
    user_processed_secs['secs_elapsed_std'] = user_secs.std()
    user_processed_secs['secs_elapsed_var'] = user_secs.var()
    user_processed_secs['secs_elapsed_skew'] = user_secs.skew()

    return user_processed_secs

raw_data_path = '../data/raw/'
processed_data_path = '../data/processed/'

global sessions

# Load raw data
train_users = pd.read_csv(raw_data_path + 'train_users.csv')
test_users = pd.read_csv(raw_data_path + 'test_users.csv')
sessions = pd.read_csv(raw_data_path + 'sessions.csv')

# Join users
users = pd.concat((train_users, test_users), axis=0, ignore_index=True)

# Drop date_first_booking column (empty since competition's restart)
users = users.drop('date_first_booking', axis=1)

# Replace NaNs
users['gender'].replace('-unknown-', np.nan, inplace=True)
users['language'].replace('-unknown-', np.nan, inplace=True)
sessions.replace('-unknown-', np.nan, inplace=True)

# Remove weird age values
users.loc[users['age'] > 100, 'age'] = np.nan
users.loc[users['age'] < 14, 'age'] = np.nan

# Change type to date
users['date_account_created'] = pd.to_datetime(users['date_account_created'])
users['date_first_active'] = pd.to_datetime(users['timestamp_first_active'],
                                            format='%Y%m%d%H%M%S')

users['weekday_account_created'] = users[
    'date_account_created'].apply(get_weekday)
users['weekday_first_active'] = users['date_first_active'].apply(get_weekday)

# Split dates into day, month, year
year_account_created = pd.DatetimeIndex(users['date_account_created']).year
users['year_account_created'] = year_account_created
month_account_created = pd.DatetimeIndex(users['date_account_created']).month
users['month_account_created'] = month_account_created
day_account_created = pd.DatetimeIndex(users['date_account_created']).day
users['day_account_created'] = day_account_created
year_first_active = pd.DatetimeIndex(users['date_first_active']).year
users['year_first_active'] = year_first_active
month_first_active = pd.DatetimeIndex(users['date_first_active']).month
users['month_first_active'] = month_first_active
day_first_active = pd.DatetimeIndex(users['date_first_active']).day
users['day_first_active'] = day_first_active

p = Pool(multiprocessing.cpu_count())
processed_sessions = p.map(process_user_session, sessions['user_id'].unique())
user_sessions = pd.DataFrame(processed_sessions).set_index('id')

# Joint the processed data with each user
users = users.set_index('id')
users = pd.concat([users, user_sessions], axis=1)

# TODO: Classify by dispositive

# Get the count of general session information
user_sessions = sessions.groupby('user_id').count()
user_sessions.rename(columns=lambda x: x + '_count', inplace=True)
users = pd.concat([users, user_sessions], axis=1)

p = Pool(multiprocessing.cpu_count())
processed_secs_elapsed = p.map(
    process_user_secs_elapsed, sessions['user_id'].unique())
processed_secs_elapsed = pd.DataFrame(processed_secs_elapsed).set_index('id')

users = pd.concat([users, processed_secs_elapsed], axis=1)

train_users = train_users.set_index('id')
test_users = test_users.set_index('id')

users.index.name = 'id'
processed_train_users = users.loc[train_users.index]
processed_test_users = users.loc[test_users.index]
processed_test_users.drop(['country_destination'], inplace=True, axis=1)

processed_train_users.to_csv(processed_data_path + 'processed_train_users.csv')
processed_test_users.to_csv(processed_data_path + 'processed_test_users.csv')

drop_list = [
    'date_account_created',
    'date_first_active',
    'timestamp_first_active'
]

# Drop columns
users = users.drop(drop_list, axis=1)

# TODO: Try with StandardScaler
# from sklearn.preprocessing import StandardScaler
# scaler = StandardScaler()
# scaler.fit_transform(users)

# Encode categorical features
categorical_features = [
    'gender', 'signup_method', 'signup_flow', 'language', 'affiliate_channel',
    'affiliate_provider', 'first_affiliate_tracked', 'signup_app',
    'first_device_type', 'first_browser', 'most_used_device'
]

users = one_hot_encoding(users, categorical_features)

processed_train_users = users.loc[train_users.index]
processed_test_users = users.loc[test_users.index]
processed_test_users.drop('country_destination', inplace=True, axis=1)

processed_train_users.to_csv(processed_data_path + 'encoded_train_users.csv')
processed_test_users.to_csv(processed_data_path + 'encoded_test_users.csv')
