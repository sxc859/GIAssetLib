import os
import json
import shutil
import hashlib
import requests
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed

# make sure hashes contains the hash for the version you aim
with open("hashes.json", "r") as f:
	hashes = json.loads(f.read())
	f.close()

with open("indexConfig.json", "r") as f:
	config = json.loads(f.read())
	f.close()

###
# warning: while these are parameters, i haven't really tested all combinations
# i use it like this, only changing version, so it may break if you do a specific run
VERSION = config["VERSION"]

DOWNLOAD_BLOCKS = config["DOWNLOAD_BLOCKS"] # set false if game already installed
BLOCKS_DIR = config["BLOCKS_DIR"] # define if download_blocks is false
BLK_CLEANUP = config["BLK_CLEANUP"]

REBUILD_MAP = config["REBUILD_MAP"] # set false if doing manually
MAP_FILE = config["MAP_FILE"] # define if rebuild_map is false
MAP_CLEANUP = config["MAP_CLEANUP"]

# don't change
EXPORT_META = config["EXPORT_META"]
GAME = config["GAME"]
HASH = hashes[VERSION]
###

int2bytes = lambda num, length=4: num.to_bytes(length, "little")
str2bytes = lambda string: string.encode("utf-8")
fixed = lambda data, size=2: data.ljust(size, b"\x00")
unfix = lambda data: data.rstrip(b"\x00")

def md5_check(fname):
	hash_md5 = hashlib.md5()
	with open(fname, "rb") as f:
		for chunk in iter(lambda: f.read(4096), b""):
			hash_md5.update(chunk)
	return hash_md5.hexdigest()

def downloadBlocks(_hash, outDir):
	baseUrl = f"https://autopatchhk.yuanshen.com/client_app/download/pc_zip/{_hash}/ScatteredFiles"
	pkgUrl = f"{baseUrl}/pkg_version"
	# blkUrl = f"{baseUrl}/GenshinImpact_Data/StreamingAssets/AssetBundles/blocks"
	# 20240301203033_RZSIny3hwJ5nq959
	# GenshinImpact_Data/StreamingAssets/AssetBundles/blocks/00/00277271.blk

	# fetch blk
	blocks = []
	totalSize = 0
	sizes = {}
	md5 = {}

	with requests.get(pkgUrl, stream=True) as response:
		response.raise_for_status()
		for line in response.iter_lines(decode_unicode=True):
			if len(line) != 0:
				file = json.loads(line)
				fname = file["remoteName"]

				if fname.endswith(".blk") and fname.startswith("GenshinImpact_Data/StreamingAssets/AssetBundles/blocks"):
					blocks.append(fname)
					totalSize += file["fileSize"]
					sizes[fname] = file["fileSize"]
					md5[fname] = file["md5"]

	print(f">>> Will download {len(blocks)} blocks | {round(totalSize / 1073741824, 2)}GB")
	os.system("pause")

	def download_block(block):
		blkUrl = f"{baseUrl}/{block}"
		blkName = os.path.basename(block)
		blkFolder = os.path.basename(os.path.dirname(block))
		blkOutDir = os.path.join(outDir, blkFolder, blkName)

		os.makedirs(os.path.dirname(blkOutDir), exist_ok=True)
		text = f"{blkFolder}//{blkName} ({round(sizes[block] / 1048576, 2)}MB)"

		if os.path.exists(blkOutDir):
			if md5_check(blkOutDir) == md5[block]:
				return f"SKIPPED -> {text}"

		try:
			with requests.get(blkUrl, stream=True) as response:
				response.raise_for_status()
				with open(blkOutDir, "wb") as file:
					for chunk in response.iter_content(1024):
						file.write(chunk)
		except:
			return f"FAILED -> {text}"
		
		return text

	with ThreadPoolExecutor(max_workers=15) as executor:
		futures = {executor.submit(download_block, block): block for block in blocks}
		
		for pos, future in enumerate(as_completed(futures), start=1):
			print(f"[{pos}/{len(blocks)}] {future.result()}")

def makeAssetMap(gameDir, outFile):
	args = [
		os.path.join(os.getcwd(), "studio", "AssetStudio.CLI.exe"),
		gameDir,
		os.getcwd(),
		"--game",
		"GI",
		"--map_op",
		"AssetMap",
		"--map_type",
		"JSON",
		"--map_name",
		outFile
	]

	subprocess.call(args)

def createMeta(blocksDir):
	file_sizes = {}
	for root, _, files in os.walk(blocksDir):
		for file in files:
			file_path = os.path.join(root, file)
			file_sizes[file.split(".")[0]] = os.path.getsize(file_path)
	return file_sizes

def createIndexFile(assetMapPath, metaData):
	data = b""

	### PARSE ###

	print("> Parsing asset map...")

	with open(assetMapPath, 'r', encoding='utf-8') as f:
		assets = json.loads(f.read())
		f.close()

	types = list(set([e["Type"] for e in assets]))
	sources = list(set([f'{os.path.basename(os.path.dirname(e["Source"]))}/{os.path.basename(e["Source"])}' for e in assets]))
	containers = list(set([e["Container"] for e in assets]))
	# folders = list(set([os.path.basename(os.path.dirname(e["Source"])) for e in assets]))

	# print(f"* {len(folders)} folders")
	print(f"* {len(assets)} assets")
	print(f"* {len(types)} types")
	print(f"* {len(sources)} sources")
	print(f"* {len(containers)} containers")

	### HEADER ###

	print("> building the index file")

	print(": header")

	header = b""
	header += b"GIAL"
	header += b"\x00\x00"
	header += b"10"
	header += b"\x00\x00"

	header += fixed(str2bytes(GAME), 4) # game id, 4 bytes
	header += fixed(str2bytes(VERSION), 4) # game ver, 4 bytes

	header += int2bytes(len(HASH), 1)
	header += str2bytes(HASH)

	data += header
	print(f"> wrote {len(header)} bytes")

	### TYPES ###

	print(": types")

	btypes = b""

	curID = 256 # 0x100
	typesRef = {}
	lenMax = max([len(e) for e in types])
	print(f"max size {lenMax}, ID start at {hex(curID)}")

	btypes += int2bytes(len(types), 1)
	btypes += int2bytes(lenMax, 1)

	for _type in types:
		btypes += int2bytes(curID, 3)
		btypes += fixed(str2bytes(_type), lenMax)
		typesRef[_type] = curID
		curID += 1

	data += btypes
	print(f"> wrote {len(btypes)} bytes")

	### SOURCES ###

	print(": sources")

	# with open(f"{GAME}{VERSION.replace('.','')}meta.json", "r") as f:
	# 	meta = json.loads(f.read())
	# 	f.close()

	meta = metaData

	bsources = bytearray()
	sources = [e.split(".")[0] for e in sources] # strip blk

	sourcesFolders = {}
	namedSources = []
	for source in sources:
		folder = source.split("/")[0]
		name = source.split("/")[-1]
		sourcesFolders[name] = int(folder)
		namedSources.append(name)

	curID += 256
	sourcesRef = {}
	lenMax = max([len(e) for e in namedSources])
	print(f"max size {lenMax}, ID start at {hex(curID)}")

	bsources += int2bytes(len(namedSources), 3)
	bsources += int2bytes(lenMax, 1)

	for source in namedSources:
		bsources += int2bytes(curID, 3)
		bsources += int2bytes(sourcesFolders[source], 1)
		bsources += fixed(str2bytes(source), lenMax)
		bsources += int2bytes(meta[source], 4)
		sourcesRef[source] = curID
		curID += 1

	data += bsources
	print(f"> wrote {len(bsources)} bytes")

	### CONTAINERS ###

	print(": containers")

	bcontainers = bytearray()

	curID += 256
	containersRef = {}
	lenMax = max([len(e) for e in containers])
	print(f"max size {lenMax}, ID start at {hex(curID)}")

	bcontainers += int2bytes(len(containers), 3)
	bcontainers += int2bytes(lenMax, 1)

	for container in containers:
		bcontainers += int2bytes(curID, 3)
		bcontainers += fixed(str2bytes(container), lenMax)
		containersRef[container] = curID
		curID += 1

	data += bcontainers
	print(f"> wrote {len(bcontainers)} bytes")

	### ASSETS ###

	print(": assets")

	bassets = bytearray()

	bassets += int2bytes(len(assets), 3)

	for asset in assets:
		# name, type, folder, source, container
		bassets += int2bytes(len(str2bytes(asset["Name"])), 1)
		bassets += str2bytes(asset["Name"])

		bassets += int2bytes(typesRef[asset["Type"]], 3)
		bassets += int2bytes(sourcesRef[os.path.basename(asset["Source"]).split(".")[0]], 3)
		bassets += int2bytes(containersRef[asset["Container"]], 3)

	data += bassets
	print(f"> wrote {len(bassets)} bytes")

	### FINAL ###

	if EXPORT_META:
		meta = {
			"types": typesRef,
			"folders": foldersRef,
			"sources": sourcesRef,
			"containers": containersRef
		}

		with open(f"{GAME}{VERSION.replace('.','')}index-meta.json", "w+") as f:
			f.write(json.dumps(meta, indent=4))
			f.close()

	out_file = f"{GAME}{VERSION.replace('.','')}.index"
	print(f">>> {out_file} ({len(data)} total bytes)")
	with open(out_file, "wb") as f:
		f.write(data)
		f.close()


# 1, have blk ready
if DOWNLOAD_BLOCKS:
	# download stuff in /blk
	BLOCKS_DIR = os.path.join(os.getcwd(), "blk")
	downloadBlocks(HASH, BLOCKS_DIR)

# return
# BLOCKS_DIR = os.path.join(os.getcwd(), "blk")

# 2, make that map
if REBUILD_MAP:
	# rebuild map with custom name
	MAP_FILE = f"{GAME}{VERSION}-map"
	makeAssetMap(BLOCKS_DIR, MAP_FILE)
	MAP_FILE = f"{MAP_FILE}.json"

# 3, make that meta
meta = createMeta(BLOCKS_DIR)

# 4, make the final index
createIndexFile(MAP_FILE, meta)

# cleanup
if BLK_CLEANUP:
	shutil.rmtree(BLOCKS_DIR)
if MAP_CLEANUP:
	os.remove(MAP_FILE)
