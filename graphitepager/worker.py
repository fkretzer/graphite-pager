from urllib import urlencode
import argparse
import datetime
import os
import time

from jinja2 import Template
import redis
import requests
import requests.exceptions

from config import get_config
from graphite_data_record import GraphiteDataRecord
from graphite_target import get_records
from level import Level
from redis_storage import RedisStorage

from notifiers.notifier_proxy import NotifierProxy
from notifiers.hipchat_notifier import HipChatNotifier
from notifiers.pagerduty_notifier import PagerdutyNotifier


ALERT_TEMPLATE = r"""{{level}} alert for {{alert.name}} {{record.target}}.  The
current value is {{current_value}} which passes the {{threshold_level|lower}}
value of {{threshold_value}}. Go to {{graph_url}}.
{% if docs_url %}Documentation: {{docs_url}}{% endif %}.
"""
HTML_ALERT_TEMPLATE = r"""{{level}} alert for {{alert.name}} {{record.target}}.
The current value is {{current_value}} which passes the
{{threshold_level|lower}} value of {{threshold_value}}.
Go to <a href="{{graph_url}}">the graph</a>.
{% if docs_url %}<a href="{{docs_url}}">Documentation</a>{% endif %}.
"""


def description_for_alert(template,
                          graphite_url,
                          alert,
                          record,
                          level,
                          current_value):
    context = dict(locals())
    context['graphite_url'] = graphite_url
    context['docs_url'] = alert.documentation_url(record.target)
    url_params = (
        ('width', 586),
        ('height', 308),
        ('target', alert.target),
        ('target', 'threshold({},"Warning")'.format(alert.warning)),
        ('target', 'threshold({},"Critical")'.format(alert.critical)),
        ('from', '-20mins'),
    )
    url_args = urlencode(url_params)
    url = '{}/render/?{}'.format(graphite_url, url_args)
    context['graph_url'] = url.replace('https', 'http')
    context['threshold_value'] = alert.value_for_level(level)
    if level == Level.NOMINAL:
        context['threshold_level'] = 'warning'
    else:
        context['threshold_level'] = level

    return Template(template).render(context)


class Description(object):

    def __init__(self, template, graphite_url, alert, record, level, value):
        self.template = template
        self.graphite_url = graphite_url
        self.alert = alert
        self.record = record
        self.level = level
        self.value = value

    def __str__(self):
        return description_for_alert(
            self.template,
            self.graphite_url,
            self.alert,
            self.record,
            self.level,
            self.value,
        )


def update_notifiers(notifier_proxy, alert, record, graphite_url):
    alert_key = '{} {}'.format(alert.name, record.target)

    alert_level, value = alert.check_record(record)

    description = Description(
        ALERT_TEMPLATE,
        graphite_url,
        alert,
        record,
        alert_level,
        value
    )
    html_description = Description(
        HTML_ALERT_TEMPLATE,
        graphite_url,
        alert,
        record,
        alert_level,
        value
    )
    if alert_level != Level.NOMINAL:
        print description

    notifier_proxy.notify(
        alert,
        alert_key,
        alert_level,
        description,
        html_description
    )


def create_notifier_proxy(config):
    redis_url = config.get('REDISTOGO_URL', config.get('REDIS_URL', None))
    STORAGE = RedisStorage(redis, redis_url)

    klasses = [
        HipChatNotifier,
        PagerdutyNotifier,
    ]

    notifier_proxy = NotifierProxy()
    for klass in klasses:
        notifier = klass(STORAGE, config)
        if notifier.enabled:
            print 'Enabling {0}'.format(notifier._domain)
            notifier_proxy.add_notifier(notifier)

    return notifier_proxy


def get_args_from_cli():
    parser = argparse.ArgumentParser(description='Run Graphite Pager')
    parser.add_argument(
        '--config',
        metavar='config',
        type=str,
        nargs=1,
        default='alerts.yml',
        help='path to the config file'
    )
    parser.add_argument(
        'command',
        nargs='?',
        choices=['run', 'verify'],
        default='run',
        help='What action to take'
    )

    args = parser.parse_args()
    return args


def verify(args):
    config = get_config(args.config[0])
    config.get_alerts()
    print 'Valid configuration, good job!'
    return


def run(args):
    config = get_config(args.config[0])
    alerts = config.get_alerts()
    notifier_proxy = create_notifier_proxy(config)
    graphite_url = config.get('GRAPHITE_URL')
    while True:
        start_time = time.time()
        seen_alert_targets = set()
        for alert in alerts:
            target = alert.target
            try:
                records = get_records(
                    graphite_url,
                    requests.get,
                    GraphiteDataRecord,
                    target,
                    from_=alert.from_,
                )
            except requests.exceptions.RequestException:
                notification = 'Could not get target: {}'.format(target)
                print notification
                notifier_proxy.notify(
                    alert,
                    target,
                    Level.CRITICAL,
                    notification,
                    notification
                )
                records = []

            for record in records:
                name = alert.name
                target = record.target
                if (name, target) not in seen_alert_targets:
                    print 'Checking', (name, target)
                    update_notifiers(
                        notifier_proxy,
                        alert,
                        record,
                        graphite_url
                    )
                    seen_alert_targets.add((name, target))
                else:
                    print 'Seen', (name, target)
        time_diff = time.time() - start_time
        sleep_for = 60 - time_diff
        if sleep_for > 0:
            sleep_for = 60 - time_diff
            print 'Sleeping for {0} seconds at {1}'.format(
                sleep_for,
                datetime.datetime.utcnow()
            )
            time.sleep(60 - time_diff)


def main():
    args = get_args_from_cli()
    if 'verify' in args.command:
        return verify(args)
    else:
        return run(args)


if __name__ == '__main__':
    main()
