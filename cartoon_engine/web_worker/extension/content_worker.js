(() => {
  const text = (el) => (el?.innerText || el?.textContent || "").trim().toLowerCase();
  const visible = (el) => !!el && !!(el.offsetWidth || el.offsetHeight || el.getClientRects().length);
  function findTextarea(){return [...document.querySelectorAll("textarea,input[type='text'],[contenteditable='true']")].filter(visible)[0]||null;}
  function findButton(words){return [...document.querySelectorAll("button,input[type='button'],input[type='submit']")].filter(visible).find(b=>words.some(w=>text(b).includes(w)));}
  function blockedReason(){const body=document.body?.innerText?.toLowerCase()||"";if(/captcha|verify you are human|i am human/.test(body))return"captcha";if(/sign in|log in|login|required account/.test(body))return"login_required";if(/rate limit|too many requests|try again later/.test(body))return"rate_limit";return null;}
  chrome.runtime.onMessage.addListener((msg,sender,sendResponse)=>{
    if(msg?.type==="KUNAL_DETECT"){const blocked=blockedReason(),input=findTextarea(),generate=findButton(["generate","start","create","run"]);sendResponse({ok:!blocked&&!!input&&!!generate,blocked,inputFound:!!input,generateFound:!!generate,url:location.href});}
    if(msg?.type==="KUNAL_SUBMIT"){const blocked=blockedReason();if(blocked)return sendResponse({ok:false,blocked});const input=findTextarea(),generate=findButton(["generate","start","create","run"]);if(!input||!generate)return sendResponse({ok:false,error:"generator_controls_not_detected"});const value=(msg.prompts||[]).join("\n");if("value"in input){const setter=Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype,"value")?.set;if(setter)setter.call(input,value);else input.value=value;}else input.textContent=value;input.dispatchEvent(new Event("input",{bubbles:true}));input.dispatchEvent(new Event("change",{bubbles:true}));generate.click();sendResponse({ok:true,submitted:msg.prompts?.length||0});}
  });
})();