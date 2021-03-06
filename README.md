Graphite Pager
==============

Graphite Pager is a small application to send notification alerts based on
Graphite metrics. This makes it easy to be paged about what's happening in
your system. It was primarily made for sending notifications using PagerDuty,
but was latter added support for other notifiers.

You shouldn't use this yet, I'm still playing with it.

It can be deployed to Heroku (make sure you use SSL!)


## Background

Graphite is a great tool for recording metrics but it isn't easy to get paged
when a metric passes a certain threshold.

Graphite-Pager is an easy to use alerting tool for Graphite that will send
notification alerts if a metric reaches a warning or critical level.


## Requirements

* Graphite
* Redis
* libmagic

## Notifiers

Notifiers are what communicate with your preferred alerting service. Currently
Graphite-Pager supports PagerDuty, HipChat and PushBullet notifications.

PagerDuty requires an application key set in the environment as `PAGERDUTY_KEY`

HipChat requires an application key `HIPCHAT_KEY` and the room to notify `HIPCHAT_ROOM`

PushBullet requires an application key `PUSHBULLET_KEY` and optionally
comma separated list of devices in `PUSHBULLET_DEVICES` and/or comma
separated list of contacts in `PUSHBULLET_CONTACTS`.

More notifiers are easy to write, file an issue if there is something you would like!

## Installation

At the moment the easiest way to install Graphite-Pager is with Heroku! See
the example at
https://github.com/philipcristiano/graphite-pager-heroku-example.

1. Install the package with Pip

`pip install -e git://github.com/philipcristiano/graphite-pager.git#egg=graphitepager`

2.  Set Environment variables
```
    GRAPHITE_USER=HTTP-basic username
    GRAPHITE_PASS=HTTP-basic password
    GRAPHITE_URL=HTTPS(hopefully) URL to your Graphite installation
    PAGERDUTY_KEY=Specific PagerDuty application key
    REDIS_URL=redis://localhost:6379/
    # REDISTOGO_URL is also supported
```
3. Set up alerts in the `alerts.yml` file

4. Run `graphite-pager`

    graphite-pager --config alerts.yml

Where the file `alerts.yml` is in the following format.

> Environment variables can also be specified in the yaml file at the top level. Simply change the casing of the environment variable to lowercase like so: `redis_url: "redis://localhost:6379/"`

# Configuration of Alerts

Configuration of alerts is handled by a YAML file. This can be verified with

    `graphite-pager verfify --config=config.yml`

If it's invalid graphite-pager will likely crash.

## Documentation url

An attribute of `docs\_uls` in the configuration will add a link to the
documentation of the alert. Currently this is in the format of
`{docs\_url}/{alert name}#{alert legend name}`

## Alert Format

Alerts have 4 required arguments and 2 optional arguments.

Required arguments:

    name - Name of thie alert group
    warning - Int for a warning value
    critical - Int for a critical value
    target - Graphtie metric to check, best if aliased

Graphite Pager understands the values for warning and critical in order to
check < and >. If warning is less than critical, values above either will
trigger an alert. If warning is greater than critical than lower values will
trigger the alert.

    Example:

        Warning: 1
        Critical: 2

        0 is fine, 3 will be critical

        Warning: 2
        Critical: 1

        0 is critical, 3 is fine.

Optional argument:

    from - The Graphite `from` parameter for how long to query for ex. `-10min` default `-1min`

    exclude - A list of targets to include. This must match the full target so it is recommended that you use the Graphite function alias() to make these readable.

### Ordering of Alerts

Alerts with the same name and target will only be checked once! This is useful
if you want to have a subset of metrics with different check times and/or
values

    Example:

        - name: Load
          target: aliasByNode(servers.worker-*.loadavg01,1)
          warning: 10
          critical: 20

        - name: Load
          target: aliasByNode(servers.*.loadavg01,1)
          warning: 5
          critical: 10

    Any worker-* nodes will alert for anything 10 or higher but the catchall
    will allow for the remaining metrics to be checked without alerting for
    worker nodes above 5


## TODO

* Create a package
* Improve URLs to the graph
* Make it easy to add new notifiers
