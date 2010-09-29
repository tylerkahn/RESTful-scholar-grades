#!/usr/bin/env python

from zope.testbrowser.browser import Browser
from pyquery import PyQuery as pq
import json
import sys

browser = Browser()

############# HELPER FUNCTIONS ################


def _compose(f, g):
	def h(x):
		return f(g(x))
	return h

def compose(listOfFunctions):
	return reduce(_compose, listOfFunctions)

def to_json(x):
		return str(x).replace("None", "null").replace("u'", "'").replace('"', '\\"').replace("'", '"').replace("True", "true").replace("False", "false")


###############################################

def logInToScholar(pid, password):
    # requires newer zope.testbrowser package 
    # browser.cookies.clearAll()
	browser.open("https://scholar.vt.edu")
	form = browser.getForm(id='loginForm')
	form.getControl(name="eid").value = pid
	form.getControl(name="pw").value = password
	form.submit()
	
def getCourseLinks():
	browser.open("https://scholar.vt.edu")
	d = pq(browser.contents)
	d = d(".termContainer").eq(0).children().eq(1).children()
	return d.map(lambda i, e: pq(e).children().attr.href)
	

def getCourseGradeBookLink(courseLink):
	browser.open(courseLink)
	d = pq(browser.contents)
	return d(".icon-sakai-gradebook-gwt-rpc").attr.href
	
def getCourseGradeJSONLink(courseGradeBookLink):
	browser.open(courseGradeBookLink)
	d = pq(browser.contents)
	s = d(".portletMainWrap").children().attr.src
	return s.replace("?panel=Main", "/gradebook/rest/application/")
		
def getJSON(courseGradeJSONLink):
	browser.open(courseGradeJSONLink)
	return json.loads(browser.contents)
	

def getCourseGradeJSON():
	# equivalent Haskell:
	# map (getJSON . getCourseGradeJSONLink . getCourseGradeBookLink) getCourseLinks	
	return map(compose([getJSON, getCourseGradeJSONLink, getCourseGradeBookLink]), getCourseLinks())

	

# Turn Scholar internal JSON to sane version
class Course:
	def __init__(self, jsonObject):
		self.masterJSONObject = jsonObject['GRADEBOOKMODELS'][0]
		userAsStudent = self.masterJSONObject['USERASSTUDENT']
		
		self.name = userAsStudent['SECTION']
		self.currentGrade = dict()
		self.currentGrade['score'] = userAsStudent['CALCULATED_GRADE']
		self.currentGrade['letter'] = userAsStudent['LETTER_GRADE']
		self.assignmentSections = self.parseAssignmentSections(self.masterJSONObject['GRADEBOOKITEMMODEL'])
	
	
	def parseAssignmentSections(self, jsonObject):
		assignmentSections = []
		try:
			# if it has multiple sections
			# TODO find a more elegant way to check if it has multiple sections
			#      than just failing if the key doesn't exist
			jsonObject['CHILDREN'][0]['CHILDREN']
			
			assignmentSectionsJSON = self.masterJSONObject['GRADEBOOKITEMMODEL']['CHILDREN']
			
			for assignmentSectionJSON in assignmentSectionsJSON:
			
				assignmentSection = dict()
				assignmentSection['name'] = assignmentSectionJSON['NAME']
				assignmentSection['assignments'] = self.parseAssignmentsInSection(assignmentSectionJSON)
				
				assignmentSections.append(assignmentSection)
		except:
			# else it doesn't have multiple sections
			assignmentSection = dict()
			assignmentSection['name'] = None
			assignmentSection['assignments'] = self.parseAssignmentsInSection(jsonObject)
			assignmentSections.append(assignmentSection)
		
		return assignmentSections

	def parseAssignmentsInSection(self, jsonObject):
		assignments = []
		if 'CHILDREN' in jsonObject: # some courses dont' have any assignments posted
			assignmentsJSON = jsonObject['CHILDREN']
			for assignmentJSON in assignmentsJSON:
				assignment = dict()
				assignmentID = str(assignmentJSON['ASSIGNMENT_ID'])
		
				assignment['name'] = assignmentJSON['NAME']
				assignment['points'] = self.masterJSONObject['USERASSTUDENT'][assignmentID]
				assignment['totalPoints'] = assignmentJSON['POINTS']
				assignment['dueDate'] = assignmentJSON['DUE_DATE']
			
				assignments.append(assignment)
		
			return assignments
		else:
			return []
	
	def __repr__(self):
		return str(dict(name = self.name,
					currentGrade = self.currentGrade,
					assignmentSections = self.assignmentSections))
				

def main(*args):
	logInToScholar(args[1], args[2])
	try:
		print to_json(map(Course, getCourseGradeJSON()))
	except:
		print "{'error':'incorrect pid or password'}"

if __name__ == "__main__":
	sys.exit(main(*sys.argv))
