path_for_examples = {
    './auth_service/.env' : './auth_service/.env-example',
    '/listing_service/.env' : './listing_service/.env-example',
    './task_service/.env' : './task_service/.env-example',
    './gateway/.env' : './gateway/.env-example',
    './.env' : './.env-example',
}

for k, v in path_for_examples.items():
    try:
        with open(v) as f:
            lines = [line.strip('\n') for line in f.readlines()]
            try:
                with open(k, 'w+') as f2:
                    for line in lines:
                        print(line, file=f2)
            except Exception as e:
                print(e)
    except Exception as e:
        print(e)
