import requests
import base64
import hmac
import hashlib
import time
import json
import slug
import logging
import inspect
import random
import string
import re
from enum import Enum

from structurizr.api import StructurizrAPI, Method

from restbakery.models import ModelBase
from restbakery.fields import *
from restbakery.complexfields import *

# Based on https://structurizr.com/help/web-api
# https://github.com/structurizr/java

# registry = {}


# class StructurizrBase(ModelBase):
# 	def __init__(self, *args, **kwargs):
# 		super().__init__(*args, **kwargs)
# 		if self.__class__._register_as not in registry:
# 			registry[self.__class__._register_as] = []
# 		registry[self.__class__._register_as].append(self)

def rnd(k=3):
	return ''.join(random.choices(string.ascii_uppercase + string.digits, k=k))


StructurizrBase = ModelBase

class Enterprise(StructurizrBase):
	name = CharField()


class Location(Enum):
	Internal = 1
	External = 2
	Unspecified = 3


class InteractionStyle(Enum):
	Synchronous = 1
	Asynchronous = 2


class Relationship(StructurizrBase):
	id = CharField()
	description = CharField()
	tags = CharField()
	sourceId = LinkField()
	destinationId = LinkField()
	url = CharField()
	technology = CharField()
	interactionStyle = EnumField(InteractionStyle)


class CanRelateTo:

	def relates_to(self, element: StructurizrBase, relationship=None):
		if relationship is None:
			relationship = Relationship()
		relationship.id = f"{self.id}_relatesto_{element.id}_{rnd()}"
		relationship.sourceId = self
		relationship.destinationId = element
		self.relationships.append(relationship)


class Person(CanRelateTo, StructurizrBase):
	id = CharField()
	name = CharField()
	description = CharField()
	tags = CharField(default='Element,Person')
	location = EnumField(Location)
	relationships = ArrayField(Relationship)
	

class Component(CanRelateTo, StructurizrBase):
	id = CharField()
	name = CharField()
	description = CharField(default="default description")
	technology = CharField()
	tags = CharField(default="Element")
	properties = DictField()
	relationships = ArrayField(Relationship)


	def __init__(self, name, **kwargs):
		super().__init__(
			id="cmp_{}_{}".format(slug.slug(name), rnd()),
			name=name,
			**kwargs
		)
		# self.properties.update(kwargs)


class Container(CanRelateTo, StructurizrBase):
	id = CharField()
	name = CharField()
	description = CharField(default="default container description")
	technology = CharField()
	properties = DictField()
	tags = CharField(default="Element")
	url = CharField()
	relationships = ArrayField(Relationship)
	components = ArrayField(Component)

	def __init__(self, name, description='', **kwargs):
		super().__init__(
			id="cnt_{}_{}".format(slug.slug(name), rnd()),
			name=name,
			**kwargs
		)

	def create_component_view(self):
		cv = ComponentView()
		cv.title = f"Component view for {self.name}"
		cv.key = slug.slug(self.name)
		cv.containerId = self.id
		for component in self.components:
			cv.addComponent(component)
		return cv

	def get_component(self, _id):
		component = next((x for x in self.components if _id in x.id), None)
		if component is None:
			raise KeyError(f"Component {_id} not found in container {self.name}")
		return component


class RankDirection(Enum):
	TopBottom = 1
	BottomTop = 2
	LeftRight = 3
	RightLeft = 4


class AutomaticLayout(StructurizrBase):
	rankDirection = EnumField(RankDirection)
	rankSeparation = IntField(default=150)
	nodeSeparation = IntField(default=100)
	edgeSeparation = IntField(default=20)
	vertices = BooleanField(default=True)


class PaperSize(Enum):
	A6_Portrait = 1
	A6_Landscape = 2
	A5_Portrait = 3
	A5_Landscape = 4
	A4_Portrait = 5
	A4_Landscape = 6
	A3_Portrait = 7
	A3_Landscape = 8
	A2_Portrait = 9
	A2_Landscape = 10
	Letter_Portrait = 11
	Letter_Landscape = 12
	Legal_Portrait = 13
	Legal_Landscape = 14
	Slide_4_3 = 15
	Slide_16_9 = 16


class View(StructurizrBase):
	
	def addPerson(self, person: Person):
		elem = Element()
		elem.id = person.id
		self.elements.append(elem)
		for rel in person.relationships:
			relview = RelationshipView()
			relview.id = rel.id
			relview.description = rel.description
			self.relationships.append(relview)



class Element(StructurizrBase):
	id = CharField()


class SoftwareSystem(CanRelateTo, StructurizrBase):
	id = CharField()
	name = CharField()
	description = CharField()
	location = EnumField(Location)
	tags = CharField(default="Element")
	containers = ArrayField(Container)
	relationships = ArrayField(Relationship)

	def create_container_view(self):
		cv = ContainerView()
		cv.title = f"Container view for {self.name}"
		cv.key = slug.slug(self.name)
		cv.softwareSystemId = self.id
		for container in self.containers:
			cv.addContainer(container)
			for relationship in container.relationships:
				cv.addContainer(relationship.destinationId)
		return cv


class RelationshipView(StructurizrBase):
	id = CharField()
	description = CharField()
	order = CharField()
	position = IntField(default=50)


class SystemLandscapeView(View):
	title = CharField()
	description = CharField()
	key = CharField()
	paperSize = EnumField(PaperSize)
	automaticLayout = ModelField(AutomaticLayout)
	enterpriseBoundaryVisible = BooleanField(True)
	elements = ArrayField(Element)
	relationships = ArrayField(RelationshipView)

	def addSoftwareSystem(self, system: SoftwareSystem):
		elem = Element()
		elem.id = system.id
		self.elements.append(elem)
		# print(self.elements)
		for rel in system.relationships:
			relview = RelationshipView()
			relview.id = rel.id
			relview.description = rel.description
			self.relationships.append(relview)


	def addAllSoftwareSystems(self):
		pass


class ContainerView(View):
	title = CharField()
	description = CharField()
	key = CharField()
	softwareSystemId = CharField()
	paperSize = EnumField(PaperSize)
	automaticLayout = ModelField(AutomaticLayout)
	elements = ArrayField(Element)
	relationships = ArrayField(RelationshipView)

	def addContainer(self, system: Container):
		elem = Element()
		elem.id = system.id
		self.elements.append(elem)
		# print(self.elements)
		for rel in system.relationships:
			relview = RelationshipView()
			relview.id = rel.id
			relview.description = rel.description
			self.relationships.append(relview)


class ComponentView(View):
	title = CharField()
	description = CharField()
	key = CharField()
	containerId = CharField()
	paperSize = EnumField(PaperSize)
	automaticLayout = ModelField(AutomaticLayout)
	elements = ArrayField(Element)
	relationships = ArrayField(RelationshipView)

	def addComponent(self, system: Container):
		elem = Element()
		elem.id = system.id
		self.elements.append(elem)
		# print(self.elements)
		for rel in system.relationships:
			relview = RelationshipView()
			relview.id = rel.id
			relview.description = rel.description
			self.relationships.append(relview)
			if not self.contains_element(rel.destinationId.id):
				_elem = Element()
				_elem.id = rel.destinationId.id
				self.elements.append(_elem)

	def contains_element(self, _id):
		element = next((x for x in self.elements if _id == x.id), None)
		return element is not None


class StructurizrModel(StructurizrBase):
	enterprise = ModelField(Enterprise)
	people = ArrayField(Person)
	softwareSystems = ArrayField(SoftwareSystem)

	def create_systemlandscape_view(self):
		slv = SystemLandscapeView()
		slv.title = f"System Landscape Diagram for {self.enterprise.name}"
		slv.key = f"SystemLandscapeView{self.enterprise.name}"
		slv.paperSize = PaperSize.A2_Landscape
		for softwareSystem in self.softwareSystems:
			slv.addSoftwareSystem(softwareSystem)
		for person in self.people:
			slv.addPerson(person)

		return slv

class Routing(Enum):
	Direct = 1
	Orthogonal = 2

class RelationshipStyle(StructurizrBase):
	tag = CharField()
	# The thickness of the line, in pixels.
	thickness = IntField(default=2)
	color = CharField(default="#aaaaaa")
	dashed = BooleanField(default=False)

	routing = EnumField(Routing)
	# The position of the annotation along the line; 0 (start) to 100 (end).
	position = IntField(default=50)
	# The opacity used when rendering the line; 0-100.
	opacity = IntField(default=80)


class Shape(Enum):
	Box = 1
	RoundedBox = 2
	Circle = 3
	Ellipse = 4
	Hexagon = 5
	Folder = 6
	Cylinder = 7 
	Pipe = 8
	WebBrowser = 9
	MobileDevicePortrait = 10
	MobileDeviceLandscape = 11
	Person = 12
	Robot = 13


class ElementStyle(StructurizrBase):
	tag = CharField()
	background = CharField(default="#ffffff")
	stroke = CharField(default="#aaaaaa")
	fontSize = IntField(default=18)
	shape = EnumField(Shape)


class Styles(StructurizrBase):
	elements = ArrayField(ElementStyle)
	relationships = ArrayField(RelationshipStyle)


class Branding(StructurizrBase):
	logo = CharField()


class Configuration(StructurizrBase):
	styles = ModelField(Styles)
	branding = ModelField(Branding)


class Views(StructurizrBase):
	systemLandscapeViews = ArrayField(SystemLandscapeView)
	containerViews = ArrayField(ContainerView)
	componentViews = ArrayField(ComponentView)
	configuration = ModelField(Configuration)


class DocumentationSection(StructurizrBase):
	title = CharField()
	content = CharField()
	format = CharField(default="Markdown")
	order = IntField()
	elementId = CharField()

	def documents(self, elem):
		self.elementId = elem.id
		self.title = elem.name

	def from_url(self, url):
		resp = requests.get(url, verify=False)
		# increase intendation level of subheadings by 1
		# top level headings are ignored
		self.content = re.sub(r"(\n?#{2})", r"\1#", resp.text)


class DecisionStatus(Enum):
	Proposed = 1
	Accepted = 2
	Superseded = 3
	Deprecated = 4
	Rejected = 5


class Decision(StructurizrBase):
	id = CharField()
	date = CharField()
	status = CharField()
	title = CharField()
	content = CharField()
	format = CharField(default="Markdown")
	elementId = CharField()

	def decision_for(self, elem):
		self.elementId = elem.id

	def from_url(self, url):
		resp = requests.get(url, verify=False)
		status_match = re.search(
			r"^> `Status: (?P<status>accepted|proposed|superseded|deprecated|rejected)",
			resp.text,
			flags=re.I | re.M
		)
		# print(resp.text)
		if status_match:
			self.status = status_match.groupdict()['status'].title()
		else:
			print(resp.text)
			raise ValueError(f"status cannot be parsed from {url}")
		date_match = re.search(
			r"^> `Date: (?P<date>[0-9]{4}-[0-9]{2}-[0-9]{2})",
			resp.text,
			flags=re.I | re.M
		)
		if date_match:
			self.date = date_match.groupdict()['date']
		else:
			raise ValueError(f"date cannot be parsed from {url}")

		title_match = re.search(
			r"^# (?P<title>.*)",
			resp.text
		)
		if title_match:
			self.title = title_match.groupdict()['title']
		else:
			ValueError(f"title cannot be parsed form {url}")

		self.content = resp.text



class Documentation(StructurizrBase):
	_count = -1
	sections = ArrayField(DocumentationSection)
	decisions = ArrayField(Decision)

	def add_doc(self, doc):
		Documentation._count += 1
		doc.order = Documentation._count
		self.sections.append(doc)

	def add_decision(self, decision):
		self.decisions.append(decision)

class Workspace(StructurizrBase):
	"""Represents a Structurizr workspace, which is a wrapper for a software architecture model, views, and documentation."""
	uri = '/workspace/{id}'

	# The workspace ID, fixed
	id = IntField()

	# The name of the workspace.
	name = CharField()

	# A short description of the workspace.
	description = CharField()

	# A version number for the workspace.
	# revision = IntField()

	# The thumbnail associated with the workspace; a Base64 encoded PNG file as a data URI (data:image/png;base64).
	thumbnail = ''

	# The last modified date, in ISO 8601 format (e.g. "2018-09-08T12:40:03Z").
	lastModifiedDate = ''

	# A string identifying the user who last modified the workspace (e.g. an e-mail address or username).
	lastModifiedUser = ''

	# A string identifying the agent that was last used to modify the workspace (e.g. "structurizr-java/1.2.0").
	lastModifiedAgent = ''

	model = ModelField(StructurizrModel)

	views = ModelField(Views)
	
	documentation = ModelField(Documentation)

	configuration = {}


	def get(self):
		response = StructurizrAPI.call(
			Method.GET,
			self.uri.format(id=self.id),
			''
		)
		if response.status_code != 200:
			print(response.status_code)
			print(response.text)
		# in the form:
		# {"id":49053,
		# "name":"Workspace 49053",
		# "description":"An empty workspace.",
		# "revision":1,
		# "lastModifiedDate":"2019-11-25T14:19:48Z",
		# "model":{},
		# "documentation":{},
		# "views":{"configuration":{"branding":{},"styles":{},"terminology":{}}}}
		# resp = response.json()
		# self.nam?e = resp.get('name', '')
		# self.description = resp.get('description', '')
		# self.revision = resp.get('revision', '')
		return response.json()


	def update(self):
		response = StructurizrAPI.call(
			Method.PUT,
			self.uri.format(id=self.id),
			json.dumps(self.serialize())
		)
		if response.status_code != 200:
			print(response.headers)
			print(response.status_code)
			print(response.text)
		else:
			payload = response.json()
			revision = payload.get('revision', 'undefined')
			print(f"successfully updated workspace to revision {payload['revision']}")