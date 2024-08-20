
const needle = require("needle")
const fs = require("fs")
const YAML = require('yaml')
const Cutter = require("mp3-cutter")

const ROOT_SLASH = "../"
const DIR = `${ROOT_SLASH}_feeds`
const feeds = []

//Get configs
fs.readdirSync(DIR).forEach(file=>{
  const fqFile = `${DIR}/${file}`
  console.log(`Got ${fqFile} @ ${DIR}/${file}`)
  const raw = fs.readFileSync(fqFile,'utf8').replace(/---/g,'')
  const yaml = YAML.parse(raw)
  yaml.path = fqFile
  yaml.handler == "grabber" && feeds.push(yaml)
})

console.log(`Config: ${JSON.stringify(feeds)}`)

class Track {
  constructor(){this.count=0;}
  add(){this.count++}
  remove(){if(--(this.count)==0) process.exit(0)}
}

const run = async()=>{
  const t = new Track()
  feeds.map(async feed=>{
    t.add()
    const f = feed
    const xml = await needle('get', f.source)
    const body = xml.body
    const firstItem = xml.body
         ?.children.find(x=>x.name=='channel')
         ?.children.find(x=>x.name=='item')
    const mediaItem = firstItem.children.find(x=> x.name == 'media:content' || x.name == 'enclosure')
    const mediaURL = mediaItem.url ? mediaItem.url : mediaItem.attributes.url
    const stream = needle.get(mediaURL,{follow_max:100})
    const outPath = `${ROOT_SLASH}${f.destination}/${f.name}.${f.extension}`
    const out = fs.createWriteStream(outPath)
    console.log(`Readable ${f.title}`)

    return stream
    .on('readable',function(){
        let chunk;
        while(chunk = this.read()){
                out.write(chunk)
        }
    })
    .on('done',function(err){
        out.close()
        console.log(`Did ${f.title}`)
        let yaml = structuredClone(f)
        delete yaml.path
        yaml.fetched = (new Date()).toISOString()
        fs.writeFileSync(f.path,`---\n${YAML.stringify(yaml)}---`)
        console.log(`Updated YAML for ${f.title}`)
        Cutter.cut({
          src: outPath,
          target: outPath,
          start: f.trim,
          end: 0
        })
        console.log(`Trimmed ${f.title}`)
        t.remove()
    })
  })
}

run()
