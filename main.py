#!/usr/bin/python
#
# Debate tournament schedule tool for Google AppEngine
#
# Copyright (c) 2008, 2010 James W. Tittsler
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
from StringIO import StringIO
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template
from google.appengine.ext.webapp.util import run_wsgi_app
from google.appengine.ext import db
from appengine_utilities.sessions import Session
#from PyRTF import *

#class Tournament(db.Model):
#    user = db.IntegerProperty()
#    uname = db.StringProperty()
#    tname = db.StringProperty()
#    nteams = db.IntegerProperty()
#    nrounds = db.IntegerProperty()
#    teams = db.StringListProperty()
#    csv = db.TextProperty()

class MainPage(webapp.RequestHandler):
  def get(self):
    self.redirect("http://www.core-ed.org/")

class Debate(webapp.RequestHandler):
    def get(self):
        self.session = Session()
        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, self.session))
    def post(self):
        self.session = Session()
        nteams = 0
        nrounds = 0
        self.session['error'] = ''

        self.session['uname'] = self.request.get('uname')
        self.session['tname'] = self.request.get('tname')

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

        if nteams > 0 and nrounds > 0 and nrounds <= ((nteams+1)/2):
            self.redirect('debate/schedule')
        else:
            self.session['error'] += 'Number of teams (%d) must be at least twice the number of rounds (%d)<br />' % (nteams, nrounds)

        path = os.path.join(os.path.dirname(__file__), 'index.html')
        self.response.out.write(template.render(path, self.session))

class DebateSchedule(webapp.RequestHandler):
    def get(self):
        self.session = Session()
        path = os.path.join(os.path.dirname(__file__), 'schedule.html')
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

        row = []
        table = '<table cellpadding=4><tr>'
        for round in range(nrounds):
            table += '<th>Round %d</th>' % (round+1)
            row.append('Round %d' % (round+1))
        table += '</tr>'

        writer.writerow(row)

        for t in range(n2):
            rowa = []
            rown = []
            if t % 2 == 0:
                table += '<tr class="evenrow">'
            else:
                table += '<tr class="oddrow">'
            for round in range(nrounds):
                table += '<td>A: %s<br />N: %s</td>' % (tc[round][t][0],
                        tc[round][t][1])
                rowa.append('A: %s' % tc[round][t][0])
                rown.append('N: %s' % tc[round][t][1])
            table += '</tr>'
            writer.writerow(rowa)
            writer.writerow(rown)
        table += '</table>'
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
                'thetable': table,
                'csv': csvs,
                }

        self.response.out.write(template.render(path, tokens))

class DebateCSV(webapp.RequestHandler):
    def get(self):
        self.session = Session()
        csv = self.session['csv']
        basename = '%s_%s' % (self.session['uname'], self.session['tname'])
        if basename == '_':
            basename = 'debate_schedule'
        basename = basename.replace(' ', '_')
        self.response.headers['Content-Type'] = 'application/csv'
        self.response.headers['Content-Disposition'] = 'inline; filename=%s.csv' % basename
        self.response.out.write(csv)

application = webapp.WSGIApplication(
                                     [('/', MainPage),
                                      ('/debate/csv', DebateCSV),
                                      ('/debate/schedule', DebateSchedule),
                                      ('/debate', Debate)],
                                     debug=True)

def main():
    run_wsgi_app(application)

if __name__ == "__main__":
    main()

