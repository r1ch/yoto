const needle = require("needle")
const fs = require("fs")

const feeds = [
  {
    title: "No Such Thing As A Fish",
    folder: "/nstaaf",
    name: "nstaaf.mp3",
    url: "https://audioboom.com/channels/2399216.rss"
  },{
    title: "Bugle",
    folder: "/bugle",
    name: "bugle.mp3",
    url: "https://feeds.acast.com/public/shows/5e7b777ba085cbe7192b0607"
  }
]

const run = async()=>{
  for(feed of feeds){
    const f = feed
    const xml = await needle('get', f.url)
    const body = xml.body
    const firstItem = xml.body
         ?.children.find(x=>x.name=='channel')
         ?.children.find(x=>x.name=='item')
    const mediaItem = firstItem.children.find(x=> x.name == 'media:content' || x.name == 'enclosure')
    const mediaURL = mediaItem.url ? mediaItem.url : mediaItem.attributes.url
    const stream = needle.get(mediaURL,{follow_max:100})
    const out = fs.createWriteStream(`${f.folder}/${f.name}`)
    console.log(`Readable ${f.title}`)

    stream
    .on('readable',function(){
        let chunk;
        while(chunk = this.read()){
                out.write(chunk)
        }
    })
    .on('done',function(err){
        console.log(`Did ${f.title}`)
        out.close()
    })
  }
}

run()
