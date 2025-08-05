path_for_envs = {
    'auth_db_url' : '../auth_service/.env',
    'listing_db_url' : '../listing_service/.env',
}

try:
    with open('.env.shared', 'w+') as env:
        urls = list()
        for key, value in path_for_envs.items():
            try:
                with open(value) as file:
                    lines = [line.strip('\n').lower() for line in file.readlines() if line.startswith("MYSQL_")]
                    env_dict = {}
                    for line in lines:
                        variable, intent = line.split('=', 1)
                        env_dict[variable] = intent
                    urls.append(
                        f'{key.upper()}=mysql+asyncmy://{env_dict['mysql_user']}:{env_dict['mysql_password']}'
                        f'@{env_dict['mysql_host']}:{env_dict['mysql_port']}/{env_dict['mysql_database']}'
                    )
            except Exception as e:
                print(e)
        for url in urls:
            print(url, file=env)
except Exception as e:
    print(e)
