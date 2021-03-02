# Next Generation of Driver Packager

- JSON instead of XML for c4zproj equivalent
- multiple build profiles in JSON
- JSON defines:
  - squish setting (and autogeneration of squishy file)
  - encrypt setting
- run LuaJIT on finished Lua structure before encrypting

`FireTV--dev.c4zproj`

```XML
<Driver type="c4z" name="FireTV" squishLua="false">
<PrepackageCommands>
	<PrepackageCommand>pandoc --metadata title="Driver Documentation" -s -H ~/c4/github-pandoc.css -o ./www/documentation.html ./documentation.md</PrepackageCommand>
	<PrepackageCommand>cp ./driver.lua ./lua/squished.lua</PrepackageCommand>
</PrepackageCommands>
<Items>
	<Item type="dir" name="www" recurse="true"/>
	<Item type="dir" name="lua" recurse="true"/>
	<Item type="dir" name="CAcerts" recurse="true"/>

	<Item type="file" name="driver.xml" c4zDir = ""/>

	<Item type="file" name="./../drivers-common-public/global/handlers.lua" c4zDir="drivers-common-public/global"/>
	<Item type="file" name="./../drivers-common-public/global/lib.lua" c4zDir="drivers-common-public/global"/>
	<Item type="file" name="./../drivers-common-public/global/msp.lua" c4zDir="drivers-common-public/global"/>
	<Item type="file" name="./../drivers-common-public/global/timer.lua" c4zDir="drivers-common-public/global"/>
	<Item type="file" name="./../drivers-common-public/global/url.lua" c4zDir="drivers-common-public/global"/>

	<Item type="file" name="./../drivers-common-public/module/json.lua" c4zDir="drivers-common-public/module"/>
	<Item type="file" name="./../drivers-common-public/module/ssdp.lua" c4zDir="drivers-common-public/module"/>

</Items>
</Driver>
```

`FireTV--prod.c4zproj`

```XML
<Driver type="c4z" name="FireTV" squishLua="true">
<PrepackageCommands>
	<PrepackageCommand>pandoc --metadata title="Driver Documentation" -s -H ~/c4/github-pandoc.css -o ./www/documentation.html ./documentation.md</PrepackageCommand>
</PrepackageCommands>
<Items>
	<Item type="dir" name="www" recurse="true"/>
	<Item type="dir" name="lua" recurse="true"/>
	<Item type="dir" name="CAcerts" recurse="true"/>

	<Item type="file" name="driver.xml" c4zDir = ""/>
</Items>
</Driver>
```

`squishy`

```text
Main "driver.lua"

-- Remote libraries --

Module "drivers-common-public.global.lib" "./../drivers-common-public/global/lib.lua"
Module "drivers-common-public.global.handlers" "./../drivers-common-public/global/handlers.lua"
Module "drivers-common-public.global.timer" "./../drivers-common-public/global/timer.lua"
Module "drivers-common-public.global.url" "./../drivers-common-public/global/url.lua"
Module "drivers-common-public.global.msp" "./../drivers-common-public/global/msp.lua"

Module "drivers-common-public.module.json" "./../drivers-common-public/module/json.lua"
Module "drivers-common-public.module.ssdp" "./../drivers-common-public/module/ssdp.lua"

-- Make Production --
Module "drivers-common-internal.global.production"		"./../drivers-common-internal/global/production.lua"

-- Driver Specific --

Output "./lua/squished.lua"
```

would become one file `c4zproj.json`

Option: parse main driver file for require statements and dynamically assemble required Lua packages?  Need hints for submodule/common/template/pre-shipped Lua files?

Option: if squish, also encrypt? Need these to be separate for any reason?

Option: write encrypted tag direct into driver based on this spec, rather than encrypting based on driver XML? Then this file is the spec, not anywhere else.


```JSON
{
	"prod": {
		"type": "c4z",
		"outputFilename": "FireTV.c4z",
		"mainDriverFile": "./lua/driver.lua",
		"encryption": true,
		"prePackageCommands": [
			"pandoc --metadata title=\"Driver Documentation\" -s -H ~/c4/github-pandoc.css -o ./www/documentation.html ./documentation.md",
		],
		"directories" : [
			{
				"source": "./lua",
				"destination": "./lua",
				"recurse": true
			}
			{
				"source": "./www",
				"destination": "./www",
				"recurse": true
			}
			{
				"source": "./CAcerts",
				"destination": "./CAcerts",
				"recurse": true
			}
		],
		"files" : [
			{
				"source": "driver.xml",
				"destination": "./"
			},
			{
				"source": "driver.lua",
				"destination": "./",
				"squish": true,
				"squishMain": true
			},
			{
				"source": "./../drivers-common-public/global/handlers.lua",
				"destination": "./drivers-common-public/global",
				"squish": true,
			},
			{
				"source": "./../drivers-common-public/global/lib.lua",
				"destination": "./drivers-common-public/global",
				"squish": true,
			},
			{
				"source": "./../drivers-common-public/global/msp.lua",
				"destination": "./drivers-common-public/global",
				"squish": true,
			},
			{
				"source": "./../drivers-common-public/global/timer.lua",
				"destination": "./drivers-common-public/global",
				"squish": true,
			},
			{
				"source": "./../drivers-common-public/global/url.lua",
				"destination": "./drivers-common-public/global",
				"squish": true,
			},
			{
				"source": "./../drivers-common-public/module/json.lua",
				"destination": "./drivers-common-public/module",
				"squish": true,
			},
			{
				"source": "./../drivers-common-public/module/ssdp.lua",
				"destination": "./drivers-common-public/module",
				"squish": true,
			}
		]
	},
	"dev": {
		"type": "c4z",
		"outputFilename": "FireTV.c4z",
		"mainDriverFile": "./lua/driver.lua",
		"encryption": true,
		"prePackageCommands": [
			"pandoc --metadata title=\"Driver Documentation\" -s -H ~/c4/github-pandoc.css -o ./www/documentation.html ./documentation.md",
			"cp ./driver.lua ./lua/squished.lua"
		],
		"postPackageCommands": [
			"rm ./lua/squished.lua"
		],
		"directories" : [
			{
				"source": "./lua",
				"destination": "./lua",
				"recurse": true
			}
			{
				"source": "./www",
				"destination": "./www",
				"recurse": true
			}
			{
				"source": "./CAcerts",
				"destination": "./CAcerts",
				"recurse": true
			}
		],
		"files" : [
			{
				"source": "driver.xml",
				"destination": "./"
			},
			{
				"source": "./../drivers-common-public/global/handlers.lua",
				"destination": "./drivers-common-public/global"
			},
			{
				"source": "./../drivers-common-public/global/lib.lua",
				"destination": "./drivers-common-public/global"
			},
			{
				"source": "./../drivers-common-public/global/msp.lua",
				"destination": "./drivers-common-public/global"
			},
			{
				"source": "./../drivers-common-public/global/timer.lua",
				"destination": "./drivers-common-public/global"
			},
			{
				"source": "./../drivers-common-public/global/url.lua",
				"destination": "./drivers-common-public/global"
			},
			{
				"source": "./../drivers-common-public/module/json.lua",
				"destination": "./drivers-common-public/module"
			},
			{
				"source": "./../drivers-common-public/module/ssdp.lua",
				"destination": "./drivers-common-public/module"
			}
		]
	}
}
```
