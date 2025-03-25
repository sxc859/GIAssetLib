import io
import os
from fileReader import FileReader

class IndexHelper:
	def __init__(self, indexFile):
		self.stream = self.getStream(indexFile)
		self.game = None
		self.version = None
		self.hash = None
		self.assets = None

		self.parse()

	def getStream(self, file):
		with open(file, "rb") as f:
			stream = io.BytesIO(f.read())
			f.close()

		return stream

	def parse(self):
		# initial check
		reader = FileReader(self.stream, "little")

		if reader.ReadBytes(4) != b"GIAL":
			raise Exception("invalid index")

		reader.ReadBytes(2)

		index_version = reader.ReadBytes(2)
		if index_version != b"\x31\x30":
			raise Exception("incompatible index version")

		reader.ReadBytes(2)

		# utils
		val = lambda length: vl2(reader.ReadBytes(length))
		vl2 = lambda data: int.from_bytes(data, "little")
		raw = lambda length: rw2(reader.ReadBytes(length))
		rw2 = lambda data: data.rstrip(b"\x00").decode("utf-8")

		# read data
		# game
		game = raw(4)

		if game != "hk4e":
			raise Exception("unknown game")

		self.game = game

		# version
		version = raw(4)

		self.version = version

		# hash
		hashSize = val(1)
		_hash = raw(hashSize)

		# types
		typesRef = {}
		nTypes = val(1)
		maxType = val(1)

		for i in range(nTypes):
			_id = val(3)
			_type = raw(maxType)
			typesRef[_id] = _type

		# sources
		nSources = val(3)
		maxSource = val(1)
		sourcesRef = {}

		for i in range(nSources):
			_id = val(3)
			folder = val(1)
			source = raw(maxSource)
			size = val(4)

			sourcesRef[_id] = {
				"block": source,
				"size": size,
				"folder": str(folder).zfill(2)
			}

		blocksRef = {}
		for source in sourcesRef.values():
			blocksRef[source["block"]] = {
				"size": source["size"],
				"folder": source["folder"]
			}

		self.blocksRef = blocksRef

		# containers
		nContainers = val(3)
		maxContainer = val(1)
		containersRef = {}

		for i in range(nContainers):
			_id = val(3)
			container = raw(maxContainer)
			containersRef[_id] = container

		# assets
		nAssets = val(3)
		assets = {}

		for i in range(nAssets):
			nameSize = val(1)
			name = raw(nameSize)

			typeId = val(3)
			_type = typesRef[typeId]

			sourceId = val(3)
			source = sourcesRef[sourceId]

			containerId = val(3)
			container = containersRef[containerId]

			assets[name] = {
				"type": _type,
				"source": source,
				"container": container
			}

		self.assets = assets

	def getBlockInfos(self, block):
		return self.blocksRef[block]
