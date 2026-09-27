const state = new Map();
async function sendToWorkerTab(workerId,message){const tabId=state.get(workerId);if(!tabId)throw new Error("worker_tab_not_found");return await chrome.tabs.sendMessage(tabId,message);}
chrome.runtime.onMessage.addListener((msg,sender,sendResponse)=>{
 if(!msg?.type)return;
 (async()=>{try{
  if(msg.type==="OPEN_WORKER_TAB"){const tab=await chrome.tabs.create({url:msg.url,active:false});state.set(msg.workerId,tab.id);sendResponse({ok:true,workerId:msg.workerId,tabId:tab.id});}
  else if(msg.type==="DETECT_GENERATOR")sendResponse(await sendToWorkerTab(msg.workerId,{type:"KUNAL_DETECT"}));
  else if(msg.type==="SUBMIT_BATCH")sendResponse(await sendToWorkerTab(msg.workerId,{type:"KUNAL_SUBMIT",prompts:msg.prompts}));
  else if(msg.type==="STOP_WORKER"){const tabId=state.get(msg.workerId);if(tabId){try{await chrome.tabs.remove(tabId)}catch{}state.delete(msg.workerId)}sendResponse({ok:true})}
 }catch(e){sendResponse({ok:false,error:String(e)})}})(); return true;
});
chrome.tabs.onRemoved.addListener(tabId=>{for(const [workerId,id] of state)if(id===tabId)state.delete(workerId)});