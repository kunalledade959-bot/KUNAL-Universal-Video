const state = { workers: new Map() };

chrome.runtime.onMessage.addListener((msg, sender, sendResponse) => {
  if (!msg || !msg.type) return;
  if (msg.type === "OPEN_WORKER_TAB") {
    chrome.tabs.create({url: msg.url, active: false}).then(tab => {
      state.workers.set(msg.workerId, tab.id);
      sendResponse({ok:true, workerId:msg.workerId, tabId:tab.id});
    }).catch(err => sendResponse({ok:false,error:String(err)}));
    return true;
  }
  if (msg.type === "STOP_WORKER") {
    const tabId=state.workers.get(msg.workerId);
    if (!tabId) { sendResponse({ok:true}); return; }
    chrome.tabs.remove(tabId).then(()=>{state.workers.delete(msg.workerId);sendResponse({ok:true});}).catch(err=>sendResponse({ok:false,error:String(err)}));
    return true;
  }
});

chrome.tabs.onRemoved.addListener((tabId) => {
  for (const [workerId,id] of state.workers) if (id===tabId) state.workers.delete(workerId);
});
