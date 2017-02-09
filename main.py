#!/usr/bin/python
#
# Debate tournament schedule tool for Google AppEngine
#
# Copyright (c) 2008, 2010, 2017 James W. Tittsler
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.

import os
import random
import csv
import codecs
from StringIO import StringIO

import jinja2
import webapp2
from webapp2_extras import sessions

JINJA_ENVIRONMENT =jinja2.Environment(
    loader=jinja2.FileSystemLoader(os.path.dirname(__file__)),
    extensions=['jinja2.ext.autoescape'],
    autoescape=True)

class UnicodeWriter:
    """
    A CSV writer which will write rows to CSV file "f",
    which is encoded in the given encoding.
    """

    def __init__(self, f, dialect=csv.excel, encoding="utf-8", **kwds):
        # Redirect output to a queue
        self.queue = StringIO()
        self.writer = csv.writer(self.queue, dialect=dialect, **kwds)
        self.stream = f
        self.encoder = codecs.getincrementalencoder(encoding)()

    def writerow(self, row):
        self.writer.writerow([s.encode("utf-8") for s in row])
        # Fetch UTF-8 output from the queue ...
        data = self.queue.getvalue()
        data = data.decode("utf-8")
        # ... and reencode it into the target encoding
        data = self.encoder.encode(data)
        # write to the target stream
        self.stream.write(data)
        # empty queue
        self.queue.truncate(0)

    def writerows(self, rows):
        for row in rows:
            self.writerow(row)

class BaseHandler(webapp2.RequestHandler):
    def dispatch(self):
        # Get a session store for this request
        self.session_store = sessions.get_store(request=self.request)

        try:
            webapp2.RequestHandler.dispatch(self)
        finally:
            self.session_store.save_sessions(self.response)

    @webapp2.cached_property
    def session(self):
        # Returns a session using the default cookie key
        return self.session_store.get_session()

class MainPage(BaseHandler):
    """
    By default, we redirect to the CORE home page
    """
    def get(self):
        self.redirect("http://www.core-ed.org/")

class Debate(BaseHandler):
    def get(self):
        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.out.write(template.render(self.session))

    def post(self):
        nteams = 0
        nrounds = 0
        self.session['error'] = ''

        self.session['uname'] = self.request.get('uname')
        self.session['tname'] = self.request.get('tname')
        mode = self.request.get('schedule')

        snrounds = self.request.get('nrounds')
        if snrounds <> '':
            nrounds = int(snrounds)
            self.session['nrounds'] = nrounds
            if nrounds <= 0:
                error += 'Number of rounds must be positive integer.<br />'

        steams = self.request.get('teams')
        teams = steams.split('\n')
        teams[:] = [x.strip() for x in teams if x.strip()]
        self.session['teams'] = teams
        nteams = len(teams)
        self.session['nteams'] = nteams

        #if nteams > 0 and nrounds > 0 and nrounds <= ((nteams+1)/2):
        if nteams > 0 and nrounds > 0 and mode == "Build Schedule":
            self.redirect('debate/schedule')
        elif nteams > 0 and nrounds > 0 and mode == "Build Schedule 2":
            self.redirect('debate/schedule2')
        else:
            self.session['error'] += 'Number of teams (%d) must be at least twice the number of rounds (%d)<br />' % (nteams, nrounds)

        template = JINJA_ENVIRONMENT.get_template('index.html')
        self.response.out.write(template.render(self.session))

class DebateSchedule(BaseHandler):
    def get(self):
        uname = self.session['uname']
        tname = self.session['tname']
        nteams = self.session['nteams']
        nrounds = self.session['nrounds']
        teams = self.session['teams']
        if len(teams) % 2 == 1:
            teams.append('- bye -')
            nteams += 1

        random.seed()
        random.shuffle(teams)

        # CSV
        csvf = StringIO()
        writer = UnicodeWriter(csvf)

        n2 = nteams/2
        a = teams[:n2]
        n = teams[n2:]
        tc = []
        for round in range(nrounds):
            col = []
            for i in range(n2):
                ai = (i + round) % n2
                ni = (i + 2*round) % n2
                if round % 2 == 0:
                    col.append((a[ai], n[ni]))
                else:
                    col.append((n[ni], a[ai]))
            tc.append(col)

        header = []
        for round in range(nrounds):
            header.append('Round %d' % (round+1))

        writer.writerow(header)

        rows = []
        for t in range(n2):
            rowa = []
            rown = []
            row = []
            for round in range(nrounds):
                rowa.append('A: %s' % tc[round][t][0])
                rown.append('N: %s' % tc[round][t][1])
                row.append((tc[round][t][0], tc[round][t][1]))
            writer.writerow(rowa)
            writer.writerow(rown)
            rows.append(row)
        pname = uname
        if uname and tname:
            pname += ": "
        pname += tname
        csvs = csvf.getvalue()
        self.session['csv'] = csvs
        csvs = csvs.replace('\n', '<br />')
        tokens = {
                'uname': uname,
                'tname': tname,
                'pname': pname,
                'nteams': nteams,
                'nrounds': nrounds,
                'n2': n2,
                'teams': teams,
                'a': a,
                'n': n,
                'header': header,
                'rows': rows,
                'csv': csvs,
                }

        template = JINJA_ENVIRONMENT.get_template('schedule.html')
        self.response.out.write(template.render(tokens))

class DebateSchedule2(BaseHandler):
    def get(self):
        uname = self.session['uname']
        tname = self.session['tname']
        nteams = self.session['nteams']
        nrounds = self.session['nrounds']
        teams = self.session['teams']
        if len(teams) % 2 == 1:
            teams.append('- bye -')
            nteams += 1

        random.seed()
        random.shuffle(teams)

        # CSV
        csvf = StringIO()
        writer = csv.writer(csvf)

        n2 = nteams/2

        tc = []
        for round in range(nrounds):
            col = []
            for i in range(n2):
                if round % 2 == 0:
                    col.append((teams[i], teams[nteams-(i+1)]))
                else:
                    col.append((teams[nteams-(i+1)], teams[i]))

            # change venues each round
            for i in range(round):
                col = col[1:] + col[0:1]

            tc.append(col)

            # rotate opponents for next round
            teams = teams[0:1] + teams[-1:] + teams[1:-1]

        header = []
        for round in range(nrounds):
            header.append('Round %d' % (round+1))

        writer.writerow(header)

        rows = []
        for t in range(n2):
            rowa = []
            rown = []
            row = []
            for round in range(nrounds):
                rowa.append('A: %s' % tc[round][t][0])
                rown.append('N: %s' % tc[round][t][1])
                row.append((tc[round][t][0], tc[round][t][1]))
            writer.writerow(rowa)
            writer.writerow(rown)
            rows.append(row)
        pname = uname
        if uname and tname:
            pname += ": "
        pname += tname
        csvs = csvf.getvalue()
        self.session['csv'] = csvs
        csvs = csvs.replace('\n', '<br />')
        tokens = {
                'uname': uname,
                'tname': tname,
                'pname': pname,
                'nteams': nteams,
                'nrounds': nrounds,
                'n2': n2,
                'teams': teams,
                #'a': a,
                #'n': n,
                'header': header,
                'rows': rows,
                'csv': csvs,
                }

        template = JINJA_ENVIRONMENT.get_template('schedule.html')
        self.response.out.write(template.render(tokens))

class DebateCSV(BaseHandler):
    def get(self):
        csv = self.session['csv']
        basename = '%s_%s' % (self.session['uname'], self.session['tname'])
        if basename == '_':
            basename = 'debate_schedule'
        basename = basename.replace(' ', '_')
        self.response.headers['Content-Type'] = 'application/csv'
        self.response.headers['Content-Disposition'] = 'inline; filename=%s.csv' % basename
        self.response.out.write(csv)

config = {}
config['webapp2_extras.sessions'] = {
        'secret_key': os.environ['COOKIE_SECRET']
        }

app = webapp2.WSGIApplication(
          [('/', MainPage),
          ('/debate/csv', DebateCSV),
          ('/debate/schedule', DebateSchedule),
          ('/debate/schedule2', DebateSchedule2),
          ('/debate', Debate)],
          debug=True,
          config=config)

