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
    const searchGroup=node('div'),pickerGroup=node('div');searchGroup.className=pickerGroup.className='ta-control-group';
    const searchLabel=node('label','Find a report instrument'),search=node('input');search.id='ta-search';search.type='search';search.placeholder='Search ticker, company or market';search.autocomplete='off';search.maxLength=120;searchLabel.htmlFor=search.id;
    const clearSearch=node('button','Clear');clearSearch.id='ta-clear';clearSearch.type='button';
    const searchLine=node('div');searchLine.className='ta-control-line';searchLine.append(search,clearSearch);searchGroup.append(searchLabel,searchLine);
    const pickerLabel=node('label','Instrument'),candidate=node('select'),showChart=node('button','Show chart');candidate.id='ta-candidate';pickerLabel.htmlFor=candidate.id;showChart.id='ta-show';showChart.type='button';
    const pickerLine=node('div');pickerLine.className='ta-control-line';pickerLine.append(candidate,showChart);pickerGroup.append(pickerLabel,pickerLine);
    const count=node('p'),selection=node('p'),context=node('p');count.id='ta-count';count.className='small';count.setAttribute('role','status');selection.id='ta-selected';context.id='ta-evidence';context.className='small';
    chips.replaceChildren(searchGroup,pickerGroup,count,selection,context);
    function label(row){return row.market+' · '+row.ticker+(row.name?' — '+row.name:'')}
    function options(){
      const previous=candidate.value,query=search.value.trim().toLocaleLowerCase();
      candidate.replaceChildren();const placeholder=node('option','Choose a matching instrument');placeholder.value='';candidate.append(placeholder);
      let matches=0;
      for(const [index,row] of rows.entries())if([row.market,row.ticker,row.name,symbol(row)||''].join(' ').toLocaleLowerCase().includes(query)){
        const option=node('option',label(row));option.value=String(index);candidate.append(option);matches++;
      }
      candidate.value=[...candidate.options].some(option=>option.value===previous)?previous:'';
      candidate.disabled=!matches;showChart.disabled=candidate.value==='';search.disabled=!rows.length;clearSearch.disabled=!rows.length;
      count.textContent=rows.length+' report instruments · '+matches+' match your search'+(!matches&&rows.length?'. No instruments match. Clear search to show all report instruments.':'');
    }
    search.oninput=options;search.onkeydown=event=>{if(event.key==='Enter')event.preventDefault()};
    clearSearch.onclick=()=>{search.value='';options();search.focus()};
    candidate.onchange=()=>{showChart.disabled=candidate.value===''};
    showChart.onclick=()=>{if(candidate.value!=='')select(Number(candidate.value))};
    function clear(){++generation;clearTimeout(timer);timer=null;observer?.disconnect();observer=null;chart.replaceChildren()}
    function select(index){
      if(destroyed||!Number.isInteger(index)||index<0||index>=rows.length)return;selected=index;clear();
      selection.textContent='Chart selected: '+label(rows[index]);
      const item=rows[index],sma=item.trend,quote=item.sessionDirection;
      const signals={bullish:'Up',up:'Up',bearish:'Down',down:'Down',neutral:'Sideways',flat:'Sideways',sideways:'Sideways'};
      const smaSignal=sma?.status==='available'&&Object.hasOwn(signals,sma.signal),quoteSignal=quote?.status==='available'&&Object.hasOwn(signals,quote.signal);
      const signal=smaSignal?sma:quoteSignal?quote:null;
      context.textContent=(smaSignal?'Historical SMA-5/SMA-20 trend: '+signals[sma.signal]:quoteSignal?'Timestamped quote direction vs previous close: '+signals[quote.signal]:'Historical trend and quote direction unavailable')+(smaSignal&&sma.last_bar_date?' · last bar '+sma.last_bar_date:'')+(quoteSignal&&quote.source_at?' · source '+quote.source_at:'')+(signal?.retrieved_at?' · retrieved '+signal.retrieved_at:'')+(signal?.reason?' · '+signal.reason:'')+'. Forecast direction remains separate; recorded forecast: '+(['up','down','flat'].includes(item.direction)?item.direction:'Unrated')+'.';
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
      if(destroyed)return;clear();selected=-1;rows=[];search.value='';candidate.value='';fallback.hidden=true;
      selection.textContent='Chart selected: none';context.textContent='';
      caption.textContent=report?.metadata?.date?'Watchlist saved: '+report.metadata.date+'. Historical SMA trend when available, otherwise timestamped quote direction. Forecast direction remains separate. Chart prices may be current or delayed, not frozen to the report date.':'Select a saved report date for its research watchlist.';
      const seen=new Set();
      for(const row of Array.isArray(report?.forecasts)?report.forecasts:[]){
        if(!row||typeof row.ticker!=='string'||!(/^[A-Z][A-Z0-9.\-]{0,14}$/.test(row.ticker)||/^\d{4}(?:EA)?$/.test(row.ticker))||!['US','MY'].includes(row.market))continue;
        const key=row.market+':'+row.ticker;if(seen.has(key))continue;seen.add(key);
        rows.push({ticker:row.ticker,market:row.market,name:typeof row.name==='string'?row.name:'',direction:row.direction,trend:row.moomoo_trend,sessionDirection:row.moomoo_session_direction});
      }
      options();if(rows.length)select(0);else status.textContent=message||'No supported tickers recorded for this report.';
    }
    function show(value){if(destroyed)return;const changed=active!==Boolean(value);active=Boolean(value);if(!active)clear();else if(changed&&selected>=0)select(selected)}
    function destroy(){if(destroyed)return;destroyed=true;active=false;clear();search.oninput=null;search.onkeydown=null;clearSearch.onclick=null;candidate.onchange=null;showChart.onclick=null}
    update(null);return {update,show,destroy};
  }
  window.PraesagusTA=Object.freeze({create,symbol,external});
})();
