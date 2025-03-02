# GIAssetLib
Get any asset (texture, model, etc) from Genshin, at any version, without having the game installed

## How to use

1. Get the tool, either by cloning (`git clone https://github.com/Escartem/GIAssetLib`) or [downloading](https://github.com/Escartem/GIAssetLib/archive/refs/heads/master.zip)
2. Install dependencies (`pip install -r requirements.txt`)
3. Run it (`python app.py`)
4. Then inside the app click on "Load Index" button
   
![image](https://github.com/user-attachments/assets/523f7775-b1b5-446e-a202-648fe31dddc7)

6. Select an index file, to get one you can see the list of [available files here](https://github.com/Escartem/GIAssetLibIndexes/tree/master), or make one yourself (see bellow section on making an index)
> [!TIP] 
> The index file have the following naming scheme : "hk4e[game version].index", so for example `hk4e54.index` is for genshin at v5.4. Unless you want to compare assets between versions, you usually need the latest one.
6. Wait for the program to load the file, and after you should have the list of all assets for that game version

![image](https://github.com/user-attachments/assets/3a3039fb-dcc8-456d-ad1e-b74701cc6704)

7. Select the assets you want from the list, you can use the search boxes too by filtering by name and type
8. Once you have your list of assets you want, click "Extract selected", the tool will inform you of the total amount of data required to download to extract the assets you selected.

![image](https://github.com/user-attachments/assets/16f23ecd-f9af-480e-90c8-e1f592fbb9f6)

9. Select your output folder, and wait for the tool to finish. And you will have your assets extracted !

## How does it work ?

Mihoyo servers provide a wonderful feature called "scattered download", allowing to download any game file, and they don't delete older versions too, so the tool shows you the existing assets, then download the required game files and extract the assets from them only, not requiring to own the full game~

## Make an index file yourself

### ⚠️ Please note the scattered files feature was added at 2.3, so you cannot build an index file earlier than 2.3

Before making an index file, first make sure the version you are aiming for is present in the file called `hashes.json` (remember it cannot work before 2.3, the hashes from 1.0 to 2.3 are only here for archival purposes), if it's in here, you're good for the next step, otherwise read the following :
- If the game version you need the hash of is the latest one, go to [hoyo-updates](https://hoyo-updates.vercel.app/), click on genshin and choose any package from the list

![image](https://github.com/user-attachments/assets/c6d6e464-6dad-43eb-a222-7fde93dc44d8)

- If the version is NOT the latest one, you need to find the download url yourself, u/SingularityHRT on reddit have been posting the links for a while now so it should do the trick, just get any link for the __**full package**__

![image](https://github.com/user-attachments/assets/195cc763-4d4a-46c1-aa76-0a4fb8d8b81f)
  
- Then cancel the download and copy the download URL, it will look like this : `https://autopatchhk.yuanshen.com/client_app/download/pc_zip/20250125201352_EiPmYLKVptWspsHf/GenshinImpact_5.4.0.zip.001`
- The hash is the text after "pc_zip", so in this case it's `20250125201352_EiPmYLKVptWspsHf`
- Add it to the hashes.json file

![image](https://github.com/user-attachments/assets/940e7af5-e142-4e22-a153-e9446f46d2a6)

---

Once you have your hash ready, open the file `createMap.py`, and look at the beginning :

```py
VERSION = "5.4"

DOWNLOAD_BLOCKS = True
BLOCKS_DIR = "H:\\Games\\GenshinImpact\\GenshinImpact_Data\\StreamingAssets\\AssetBundles\\blocks"
BLK_CLEANUP = True

REBUILD_MAP = True
MAP_FILE = "gi54f.json"
MAP_CLEANUP = True
```

- **VERSION** : set it to the version you are aiming for
- **DOWNLOAD_BLOCKS** : set to True if you want the script to download the game data itself, useful if you do not have the game at that version on your PC, otherwise set to False
- **BLOCKS_DIR** : if you set download_blocks to false, place here the path to your game "blocks" directory, use the example path above to figure it out, **make sure to use double backslashes to not have formatting errors after !!**
- **BLK_CLEANUP** : if you set download_blocks to true, this will define if the downloaded game data is automatically deleted at the end
- **REBUILD_MAP** : set to true if you want to have the tool build the asset map itself
- **MAP_FILE** : if you set rebuild_map to false, place here the name of the asset map you made, it must be in the same folder. If you already have the game data and made the map yourself, DO NOT DELETE THE GAME DATA, the tool uses it afterwards again.
- **MAP_CLEANUP** : same logic as blk_cleanup, deletes the map at the end

Once everything is defined as you wish, run `python createMap.py` and wait for the tool to finish, if you asked it to download the game data itself, it will show you the download size and ask for confirmation before starting. Then at the end you will have your index file~
