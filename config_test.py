import configparser

config = configparser.ConfigParser()
config.read('config.ini')
for x in config['Sections']:
    print(x, config['Sections'][x])

print(config['Telegram']['BOT_API_TOKEN'])