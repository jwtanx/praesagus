/* Hosted widget contract: https://www.tradingview.com/widget-docs/widgets/charts/advanced-chart/
 * Curated exchange keys verified against TradingView /symbols/EXCHANGE-TICKER/ pages.
 * Unknown listings require review before adding a mapping; never guess an exchange or Bursa alias.
 */
(function(){
  'use strict';
  // Reviewed symbol identities (2026-10-03); these do not establish widget/data entitlement.
  const US=Object.freeze({SPY:'AMEX:SPY',IWM:'AMEX:IWM',QQQ:'NASDAQ:QQQ',AAPL:'NASDAQ:AAPL',
    MSFT:'NASDAQ:MSFT',GOOGL:'NASDAQ:GOOGL',NVDA:'NASDAQ:NVDA',AVGO:'NASDAQ:AVGO',WMT:'NASDAQ:WMT',
    TSLA:'NASDAQ:TSLA',LIN:'NASDAQ:LIN',JPM:'NYSE:JPM',GS:'NYSE:GS',V:'NYSE:V',TSM:'NYSE:TSM',
    LLY:'NYSE:LLY',JNJ:'NYSE:JNJ',ABT:'NYSE:ABT',PG:'NYSE:PG',KO:'NYSE:KO',HD:'NYSE:HD',MCD:'NYSE:MCD',
    XOM:'NYSE:XOM',COP:'NYSE:COP',SLB:'NYSE:SLB',CAT:'NYSE:CAT',GE:'NYSE:GE',UPS:'NYSE:UPS',FCX:'NYSE:FCX',NEM:'NYSE:NEM'});
  const MY=Object.freeze({'0820EA':'MYX:F4GBM-EA','0800EA':'MYX:ABFMY1','1155':'MYX:MAYBANK',
    '1023':'MYX:CIMB','0277':'MYX:CLOUDPT','0259':'MYX:SNS','0166':'MYX:INARI','0097':'MYX:VITROX',
    '5225':'MYX:IHH','5878':'MYX:KPJ','4707':'MYX:NESTLE','3689':'MYX:F&N','5296':'MYX:MRDIY',
    '4715':'MYX:GENM','6033':'MYX:PETGAS','5681':'MYX:PETDAG','5246':'MYX:WPRTS','3816':'MYX:MISC',
    '1961':'MYX:IOICORP','5285':'MYX:SDG'});
  const SCRIPT='https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js';
  function symbol(row){
    const table=row?.market==='US'?US:row?.market==='MY'?MY:null;
    return table&&typeof row.ticker==='string'&&Object.hasOwn(table,row.ticker)?table[row.ticker]:null;
  }
  function external(row){const mapped=symbol(row);return mapped?'https://www.tradingview.com/chart/?symbol='+encodeURIComponent(mapped):'https://www.tradingview.com/symbols/'}
  function node(tag,text){const el=document.createElement(tag);if(text!==undefined)el.textContent=text;return el}
  function create(root){
    const chips=root.querySelector('#ta-chips'),chart=root.querySelector('#ta-chart'),status=root.querySelector('#ta-status'),caption=root.querySelector('#ta-caption'),fallback=root.querySelector('#ta-external');
    let rows=[],selected=-1,active=false,generation=0,timer=null,observer=null,destroyed=false;
    const reduced=window.matchMedia?.('(prefers-reduced-motion: reduce)'),listeners=[];
    let frame=null,lastTime=null,period=0,offset=0,hover=false,focused=false,paused=false,manual=false,inViewport=false,idleTimer=null;
    const pointers=new Set(),touches=new Set();
    let windowBlurred=false;
    function listen(target,type,fn,options){target?.addEventListener?.(type,fn,options);listeners.push(()=>target?.removeEventListener?.(type,fn,options))}
    function stopMotion(){if(frame!==null)window.cancelAnimationFrame(frame);frame=null;lastTime=null}
    function canMove(){return !destroyed&&active&&inViewport&&!document.hidden&&!reduced?.matches&&!hover&&!focused&&!paused&&!manual&&!windowBlurred&&!pointers.size&&!touches.size&&rows.length>1&&period>chips.clientWidth}
    function rebuildTape(){
      if(destroyed)return;
      stopMotion();
      for(const copy of chips.querySelectorAll('[data-tape-copy]'))copy.remove();
      period=0;offset=0;
      const buttons=[...chips.children];
      if(rows.length>1&&buttons.length){
        const gap=parseFloat(window.getComputedStyle(chips).gap)||0;
        const first=buttons[0],last=buttons.at(-1);
        const firstRect=first.getBoundingClientRect(),lastRect=last.getBoundingClientRect();
        const extent=lastRect.right-firstRect.left||last.offsetLeft+last.offsetWidth-first.offsetLeft;
        const width=extent||chips.scrollWidth;
        if(width>chips.clientWidth){
          period=width+gap;
          for(const [index,button] of buttons.entries()){
            // Decorative spans cannot enter the accessibility tree or receive focus.
            const copy=node('span');copy.className=button.className;copy.dataset.tapeCopy=String(index);
            copy.setAttribute('aria-hidden','true');copy.title=button.title;
            copy.append(button.firstChild.cloneNode(true));
            const buttonWidth=button.getBoundingClientRect().width||button.offsetWidth;
            if(buttonWidth)copy.style.width=buttonWidth+'px';
            copy.style.font=window.getComputedStyle(button).font;
            copy.classList.toggle('ta-chip-selected',index===selected);
            copy.onclick=()=>{manualPause();select(index)};chips.append(copy);
          }
          offset=((chips.scrollLeft%period)+period)%period;chips.scrollLeft=offset;
        }else chips.scrollLeft=0;
      }
      syncMotion();
    }
    function tick(now){
      frame=null;if(!canMove()){lastTime=null;return}
      // Accumulate fractions independently of rounded browser scroll readback.
      // Copies at one measured period have identical pixels; modulo connects end to start.
      if(lastTime!==null){offset=(offset+Math.min(64,Math.max(0,now-lastTime))/1000*12)%period;chips.scrollLeft=offset;}
      lastTime=now;frame=window.requestAnimationFrame(tick);
    }
    function syncMotion(){
      if(!canMove()){stopMotion();return}if(frame===null){offset=((chips.scrollLeft%period)+period)%period;frame=window.requestAnimationFrame(tick)}
    }
    function clearIdle(){clearTimeout(idleTimer);idleTimer=null}
    function manualPause(){clearIdle();if(paused)return;manual=true;syncMotion();idleTimer=setTimeout(()=>{idleTimer=null;manual=false;syncMotion()},5000)}
    listen(chips,'mouseenter',()=>{hover=true;syncMotion()});listen(chips,'mouseleave',()=>{hover=false;syncMotion()});
    listen(chips,'focusin',()=>{focused=true;syncMotion()});listen(chips,'focusout',event=>{focused=chips.contains(event.relatedTarget);syncMotion()});
    listen(chips,'pointerdown',event=>{pointers.add(event.pointerId??'legacy');manualPause()},{passive:true});
    listen(chips,'touchstart',event=>{for(const touch of event.changedTouches||[{identifier:'legacy'}])touches.add(touch.identifier);manualPause()},{passive:true});
    function releasePointer(event){if(pointers.delete(event.pointerId??'legacy'))manualPause()}
    function releaseTouch(event){let released=false;for(const touch of event.changedTouches||[{identifier:'legacy'}])released=touches.delete(touch.identifier)||released;if(released)manualPause()}
    for(const type of ['pointerup','pointercancel'])listen(window,type,releasePointer,{capture:true,passive:true});
    for(const type of ['touchend','touchcancel'])listen(window,type,releaseTouch,{capture:true,passive:true});
    for(const type of ['touchmove','wheel'])listen(chips,type,manualPause,{passive:true});
    listen(window,'blur',()=>{windowBlurred=true;pointers.clear();touches.clear();manualPause();syncMotion()});
    listen(window,'focus',()=>{windowBlurred=false;syncMotion()});
    listen(chips,'pointermove',event=>{if(event.buttons)manualPause()},{passive:true});
    listen(chips,'keydown',event=>{if(event.key==='Escape'){paused=true;manual=false;clearIdle();syncMotion()}else manualPause()});
    listen(document,'visibilitychange',syncMotion);listen(window,'resize',rebuildTape);listen(reduced,'change',syncMotion);
    const tapeResize=typeof ResizeObserver==='function'?new ResizeObserver(rebuildTape):null;
    tapeResize?.observe(chips);
    const visibility=typeof IntersectionObserver==='function'?new IntersectionObserver(entries=>{inViewport=entries.some(entry=>entry.isIntersecting);syncMotion()}):null;
    if(visibility)visibility.observe(chips);else inViewport=true;
    function clear(){++generation;clearTimeout(timer);timer=null;observer?.disconnect();observer=null;chart.replaceChildren()}
    function select(index){
      if(destroyed||index<0||index>=rows.length)return;selected=index;clear();
      [...chips.children].forEach((button,i)=>{if(button.dataset.tapeCopy!==undefined)button.classList.toggle('ta-chip-selected',Number(button.dataset.tapeCopy)===index);else button.setAttribute('aria-pressed',String(i===index))});
      const row=rows[index],mapped=symbol(row);fallback.href=external(row);fallback.hidden=false;
      fallback.textContent=mapped?'Open '+mapped+' on TradingView (availability unverified)':'Find symbol on TradingView (identity unverified)';
      if(!mapped){status.textContent=row.market==='MY'?'No curated Bursa identity; use TradingView symbol search.':'No curated US exchange mapping; embedded chart unavailable.';return}
      if(!active){status.textContent='Chart attempt starts when Technical analysis is opened; data availability is unverified.';return}
      const token=generation,container=node('div');container.className='tradingview-widget-container';container.style.height='100%';container.style.width='100%';
      const widget=node('div');widget.className='tradingview-widget-container__widget';widget.style.height='calc(100% - 32px)';widget.style.width='100%';container.append(widget);
      const copyright=node('div');copyright.className='tradingview-widget-copyright';const credit=node('a','Track all markets on TradingView');credit.href='https://www.tradingview.com/';credit.target='_blank';credit.rel='noopener noreferrer';copyright.append(credit);container.append(copyright);
      const script=node('script');script.src=SCRIPT;script.type='text/javascript';script.async=true;
      script.textContent=JSON.stringify({autosize:true,symbol:mapped,interval:'D',timezone:'Etc/UTC',theme:'dark',style:'1',locale:'en',allow_symbol_change:false,calendar:false,support_host:'https://www.tradingview.com'});
      status.textContent='Loading hosted chart; data availability is unverified. The external link remains available.';
      const fail=()=>{if(token!==generation||!active)return;clear();status.textContent='Hosted chart unavailable or blocked. Use the external TradingView link.'};
      script.onerror=fail;
      // Script load alone does not establish chart/data availability. Observe only embed presence.
      observer=new MutationObserver(()=>{if(token!==generation)return;const frame=container.querySelector('iframe');if(frame){frame.title='TradingView current/delayed chart for '+row.ticker;clearTimeout(timer);status.textContent='Hosted chart frame added. Data availability/delay remains unverified; check TradingView. The external link remains available.'}});
      observer.observe(container,{childList:true,subtree:true});container.append(script);chart.append(container);timer=setTimeout(()=>{if(!container.querySelector('iframe'))fail()},15000);
    }
    function update(report,message){
      if(destroyed)return;clearIdle();manual=false;stopMotion();clear();selected=-1;chips.replaceChildren();chips.scrollLeft=0;period=0;offset=0;focused=chips.contains(document.activeElement);rows=[];fallback.hidden=true;
      caption.textContent=report?.metadata?.date?'Watchlist from '+report.metadata.date+'. Chart prices are current or delayed, not frozen to the report date. Ticker colors and icons show the recorded report scenario, not a live price signal.':'Select a saved report date for its research watchlist.';
      const seen=new Set();
      for(const row of Array.isArray(report?.forecasts)?report.forecasts:[]){if(!row||typeof row.ticker!=='string'||!(/^[A-Z][A-Z0-9.\-]{0,14}$/.test(row.ticker)||/^\d{4}(?:EA)?$/.test(row.ticker))||!['US','MY'].includes(row.market))continue;const key=row.market+':'+row.ticker;if(seen.has(key))continue;seen.add(key);rows.push({ticker:row.ticker,market:row.market,direction:row.direction})}
      for(const [index,row] of rows.entries()){
        const directions={up:['📈','Up','up'],down:['📉','Down','down'],flat:['↔️','Flat','flat']},[emoji,label,color]=(typeof row.direction==='string'&&Object.hasOwn(directions,row.direction)?directions[row.direction]:['❔','Unrated','unrated']);
        const button=node('button'),inner=node('span',emoji+' '+row.ticker);inner.className='ta-chip-label';button.append(inner);button.type='button';button.className='ta-chip ta-'+color;button.setAttribute('aria-label',row.market+' '+row.ticker+' · '+label+' report scenario');button.title=row.market+' '+row.ticker+' · '+label+' recorded report scenario';button.setAttribute('aria-pressed','false');button.onclick=()=>{manualPause();select(index)};
        button.onkeydown=event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const target=event.key==='Home'?0:event.key==='End'?rows.length-1:(index+(event.key==='ArrowRight'?1:-1)+rows.length)%rows.length;chips.children[target].focus();chips.children[target].scrollIntoView({block:'nearest',inline:'nearest',behavior:window.matchMedia?.('(prefers-reduced-motion: reduce)').matches?'auto':'smooth'})};chips.append(button);
      }
      if(rows.length)select(0);else status.textContent=message||'No supported tickers recorded for this report.';rebuildTape();
    }
    function show(value){if(destroyed)return;const changed=active!==value;active=value;if(!active){clear();clearIdle();manual=false}else if(changed&&selected>=0)select(selected);if(active&&changed)rebuildTape();else syncMotion()}
    function destroy(){if(destroyed)return;destroyed=true;active=false;pointers.clear();touches.clear();clearIdle();stopMotion();clear();visibility?.disconnect();tapeResize?.disconnect();listeners.forEach(remove=>remove());for(const button of chips.children){button.onclick=null;button.onkeydown=null}}
    update(null);return {update,show,destroy};
  }
  window.PraesagusTA=Object.freeze({create,symbol,external});
})();
