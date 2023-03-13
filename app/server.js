const express = require("express");
const path = require("path");
let app = express();
const port = 6060;
app.use(express.static(path.join(__dirname,'dist')))

app.get('/',(req,res)=>{
  res.sendFile(__dirname+'/dist/index.html')
})
app.listen(port, () => {
  console.log(`Express is running on port  http://localhost:${port}`);
});