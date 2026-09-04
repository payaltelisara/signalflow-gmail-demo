const leads = [
  {name:'Maya Chen', initials:'MC', role:'VP, Revenue Operations', company:'Lumen Health', score:96, stage:'Qualified', source:'Website demo request', intent:'High', owner:'Priya Shah', timeline:['Demo request received','Sample firmographics enriched','ICP score calculated: 96/100','Assigned to Priya']},
  {name:'Jordan Blake', initials:'JB', role:'Head of Growth', company:'Orbitly', score:91, stage:'Meeting booked', source:'Cold email reply', intent:'High', owner:'Marcus Lee', timeline:['Replied to EMEA campaign','Sample reply event matched','Meeting booked in demo flow','Opportunity created']},
  {name:'Sofia Patel', initials:'SP', role:'Director of Sales', company:'NexaCloud', score:87, stage:'Qualified', source:'LinkedIn outreach', intent:'High', owner:'Priya Shah', timeline:['Imported from outreach','Pricing engagement modeled','Fit score changed from 68 to 87','Assigned to Priya']},
  {name:'Ethan Ross', initials:'ER', role:'Founder & CEO', company:'Tandem AI', score:76, stage:'Nurturing', source:'Partner referral', intent:'Medium', owner:'Marcus Lee', timeline:['Partner referral submitted','Company enriched','Entered founder nurture sequence']},
  {name:'Amara Okafor', initials:'AO', role:'Operations Lead', company:'Brightpath', score:68, stage:'Needs action', source:'CSV import', intent:'Medium', owner:'Unassigned', timeline:['CSV batch imported','Duplicate check passed','Awaiting territory assignment']}
];

const campaigns = [
  {id:'emea', name:'EMEA revenue leaders', status:'Active', prospects:42, steps:3, delivered:'612', reply:'14.1%', meetings:8, note:'Prioritizes revenue leaders at companies showing hiring momentum.'},
  {id:'inbound', name:'Inbound demo follow-up', status:'Active', prospects:18, steps:2, delivered:'284', reply:'18.6%', meetings:6, note:'A short follow-up for high-intent inbound leads.'},
  {id:'founder', name:'Founder nurture', status:'Draft', prospects:26, steps:4, delivered:'—', reply:'—', meetings:0, note:'Awaiting review before the sample sequence is activated.'}
];

const activity = [['↳','Maya Chen','submitted a demo request','2m'],['✉','Jordan Blake','replied to Campaign: EMEA revenue leaders','12m'],['◫','Sofia Patel','moved to Qualified','24m'],['◷','System','routed 6 new leads to owners','41m'],['◉','Ethan Ross','was referred by Acme Partners','1h']];
const research = [
  {name:'Maya Chen', company:'Lumen Health', insight:'Hiring three RevOps roles, suggesting active process change.', status:'Ready'},
  {name:'Jordan Blake', company:'Orbitly', insight:'Recent pricing engagement and a positive campaign reply.', status:'Ready'},
  {name:'Sofia Patel', company:'NexaCloud', insight:'Expansion signal found in the modeled account brief.', status:'Queued'}
];

let selectedLead = leads[0], selectedCampaign = campaigns[0], filter = 'all', dialogMode = 'lead', nextLeadNumber = 1;
const $ = selector => document.querySelector(selector);
const $$ = selector => [...document.querySelectorAll(selector)];
const scoreClass = score => score >= 85 ? 'high' : score >= 70 ? 'mid' : 'low';
const statusClass = status => status.toLowerCase().replace(/\s+/g, '-');

function showToast(message) { const toast = $('#toast'); toast.textContent = message; toast.classList.add('show'); setTimeout(() => toast.classList.remove('show'), 2700); }

function renderLeads() {
  const shown = leads.filter(lead => filter === 'all' || filter === 'needs' && lead.stage === 'Needs action' || filter === 'hot' && lead.intent === 'High');
  $('#leadList').innerHTML = shown.map(lead => `<article class="lead-row" data-index="${leads.indexOf(lead)}" tabindex="0" role="button" aria-label="Open ${lead.name}"><span class="lead-avatar">${lead.initials}</span><span><span class="lead-name">${lead.name}</span><span class="lead-role">${lead.role}</span></span><span class="company">${lead.company}</span><span class="score ${scoreClass(lead.score)}">${lead.score} score</span><span class="lead-arrow">›</span></article>`).join('');
  $$('.lead-row').forEach(row => { const open = () => openLead(leads[row.dataset.index]); row.addEventListener('click', open); row.addEventListener('keydown', event => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); open(); } }); });
  $('#leadCount').textContent = leads.length;
}

function renderActivity() { $('#activityList').innerHTML = activity.map(item => `<div class="event"><span class="event-icon">${item[0]}</span><p><b>${item[1]}</b> ${item[2]}</p><time>${item[3]}</time></div>`).join(''); }

function renderCampaigns() {
  $('#campaignList').innerHTML = campaigns.map(campaign => `<button class="campaign-row ${selectedCampaign.id === campaign.id ? 'selected' : ''}" type="button" data-campaign="${campaign.id}"><span><b>${campaign.name}</b><small>${campaign.prospects} prospects · ${campaign.steps} email steps · owner: Payal</small><i class="step-track">${Array.from({length: campaign.steps}, () => '<em></em>').join('')}</i></span><strong class="campaign-status ${statusClass(campaign.status)}">${campaign.status}</strong></button>`).join('');
  $$('.campaign-row').forEach(row => row.addEventListener('click', () => { selectedCampaign = campaigns.find(campaign => campaign.id === row.dataset.campaign); renderCampaigns(); renderCampaignDetail(); }));
  $('#activeCampaignCount').textContent = campaigns.filter(campaign => campaign.status === 'Active').length;
}

function renderCampaignDetail() {
  const campaign = selectedCampaign;
  $('#campaignDetail').innerHTML = `<div class="panel-heading"><div><h2>${campaign.name}</h2><p>${campaign.note}</p></div><span class="campaign-status ${statusClass(campaign.status)}">${campaign.status}</span></div><div class="campaign-detail-metrics"><div><span>Delivered</span><b>${campaign.delivered}</b></div><div><span>Reply rate</span><b>${campaign.reply}</b></div><div><span>Meetings</span><b>${campaign.meetings}</b></div></div><button class="primary-btn" id="campaignAction" type="button">${campaign.status === 'Active' ? 'Pause campaign' : 'Activate campaign'}</button><p class="detail-note">Status updates are stored only in this browser tab.</p>`;
  $('#campaignAction').addEventListener('click', () => { selectedCampaign.status = selectedCampaign.status === 'Active' ? 'Paused' : 'Active'; renderCampaigns(); renderCampaignDetail(); showToast(`${selectedCampaign.name} ${selectedCampaign.status === 'Active' ? 'activated' : 'paused'}`); });
}

function renderResearch() {
  $('#researchList').innerHTML = research.map(item => `<button class="research-row" type="button" data-research="${item.name}"><span><b>${item.name}</b><small>${item.company} · ${item.insight}</small></span><span class="research-status ${item.status.toLowerCase()}">${item.status}</span></button>`).join('');
  $$('.research-row').forEach(row => row.addEventListener('click', () => { const item = research.find(entry => entry.name === row.dataset.research); openInfo(`${item.name} research`, item.insight, ['Source: simulated account and contact record', 'Confidence: modeled for public demo', 'No external research service was called']); }));
}

function openLead(lead) { dialogMode = 'lead'; selectedLead = lead; $('#advanceLead').hidden = false; $('#advanceLead').textContent = 'Advance stage'; $('#dialogContent').innerHTML = `<h2>${lead.name}</h2><p class="dialog-company">${lead.role} at ${lead.company}</p><div class="detail-grid"><div>Lead score<b>${lead.score} / 100</b></div><div>Stage<b>${lead.stage}</b></div><div>Source<b>${lead.source}</b></div><div>Owner<b>${lead.owner}</b></div></div><div class="timeline">${lead.timeline.map(item => `<p>${item}</p>`).join('')}</div>`; $('#leadDialog').showModal(); }
function openInfo(title, copy, items = []) { dialogMode = 'info'; $('#advanceLead').hidden = true; $('#dialogContent').innerHTML = `<h2>${title}</h2><p class="dialog-company">${copy}</p><div class="timeline">${items.map(item => `<p>${item}</p>`).join('')}</div>`; $('#leadDialog').showModal(); }

function setView(view) {
  const content = {overview:['Good morning, Payal.','Here is what needs attention in your pipeline.'],leads:['Lead workspace','Review priority records and advance their simulated stages.'],pipeline:['Pipeline overview','31 open opportunities across qualification, outreach, and meetings.'],campaigns:['Campaign command center','Operate simulated cold-email campaigns and GTM intelligence from one workspace.'],insights:['Insights','Inspect modeled source mix and qualification signals.'],settings:['Workspace settings','Your showcase uses local, in-browser sample data only.']};
  const [title, subtitle] = content[view] || content.overview; $('#pageTitle').textContent = title; $('#pageSubtitle').textContent = subtitle; $$('[data-view]').forEach(link => link.classList.toggle('active', link.dataset.view === view));
  const campaignView = $('#campaignView'), base = [$('.metrics'), $('.content-grid')], context = $('#viewContext');
  if (view === 'campaigns') { campaignView.hidden = false; base.forEach(section => section.hidden = true); context.hidden = true; renderCampaigns(); renderCampaignDetail(); renderResearch(); }
  else { campaignView.hidden = true; base.forEach(section => section.hidden = false); if (view === 'overview' || view === 'leads') context.hidden = true; else { const details = {pipeline:['31 open opportunities','19 meetings booked','7 opportunities created this month'],insights:['Website drives 42% of modeled leads','High intent leads are prioritized first','Qualification rules are visible on every lead'],settings:['Data mode: simulated','Email sending: disabled','Workspace: Northstar Health']}[view]; context.innerHTML = `<div><strong>${title}</strong><span>${subtitle}</span></div><div class="context-points">${details.map(item => `<span>${item}</span>`).join('')}</div>`; context.hidden = false; } }
  if (view === 'leads') setTimeout(() => $('#leads').scrollIntoView({behavior:'smooth', block:'start'}), 0); history.replaceState(null, '', `#${view}`);
}

$$('.filter').forEach(button => button.addEventListener('click', () => { filter = button.dataset.filter; $$('.filter').forEach(item => item.classList.toggle('active', item === button)); renderLeads(); }));
$('#advanceLead').addEventListener('click', event => { event.preventDefault(); if (dialogMode !== 'lead') return; const next = {'Needs action':'Qualified', Qualified:'Sequence enrolled', Nurturing:'Qualified', 'Meeting booked':'Opportunity created'}; selectedLead.stage = next[selectedLead.stage] || 'Closed won'; selectedLead.timeline.unshift(`Stage advanced to ${selectedLead.stage}`); $('#leadDialog').close(); showToast(`${selectedLead.name} advanced to ${selectedLead.stage}`); renderLeads(); });
$('#newLead').addEventListener('click', () => { const lead = {name:`Avery Morgan ${nextLeadNumber}`, initials:'AM', role:'Growth Operations', company:'New prospect', score:72, stage:'Needs action', source:'Manual demo intake', intent:'Medium', owner:'Unassigned', timeline:['Added from the interactive demo','Ready for qualification and routing']}; nextLeadNumber++; leads.unshift(lead); filter = 'all'; $$('.filter').forEach(item => item.classList.toggle('active', item.dataset.filter === 'all')); renderLeads(); openLead(lead); showToast(`${lead.name} added to the showcase`); });
$('#notifications').addEventListener('click', () => openInfo('Notifications','Three sample notifications need review.',['Maya Chen submitted a demo request · 2 minutes ago','Jordan Blake replied to EMEA revenue leaders · 12 minutes ago','Six leads were routed by the modeled assignment rule · 41 minutes ago']));
$('#viewAll').addEventListener('click', () => { filter = 'all'; $$('.filter').forEach(item => item.classList.toggle('active', item.dataset.filter === 'all')); renderLeads(); setView('leads'); showToast('Showing all priority leads'); });
$('#sourceReport').addEventListener('click', () => openInfo('Lead source report','Modeled source mix for the static showcase.',['Website · 54 leads · 42%','Outbound · 36 leads · 28%','Partners · 23 leads · 18%','Other · 15 leads · 12%']));
$('#workspaceSwitcher').addEventListener('click', event => { const expanded = event.currentTarget.getAttribute('aria-expanded') === 'true'; event.currentTarget.setAttribute('aria-expanded', String(!expanded)); showToast(expanded ? 'Workspace switcher closed' : 'Northstar Health is the active workspace'); });
$('#userMenu').addEventListener('click', () => openInfo('Payal','Revenue admin for the Northstar Health showcase.',['Access level: Revenue admin','Data source: local simulated records','Email delivery: disabled for this public demo']));
$$('[data-view]').forEach(link => link.addEventListener('click', event => { event.preventDefault(); setView(link.dataset.view); }));
$('#newCampaign').addEventListener('click', () => showToast('Campaign builder is available in this simulated demo'));
$('#editIcp').addEventListener('click', () => openInfo('ICP profile','The target profile is modeled for this public demo.',['Company size: 50–500 employees','Industries: B2B SaaS and Healthtech','Buyer: Revenue or Growth leadership','Trigger: hiring or new funding']));
$('#runEnrichment').addEventListener('click', event => { const button = event.currentTarget; button.disabled = true; button.textContent = 'Enriching…'; $('#enrichmentState').textContent = 'Running'; setTimeout(() => { button.disabled = false; button.textContent = 'Run enrichment'; $('#enrichmentState').textContent = 'Ready'; showToast('6 sample prospects enriched'); }, 900); });
$('#runResearch').addEventListener('click', event => { const button = event.currentTarget; button.disabled = true; button.textContent = 'Researching…'; setTimeout(() => { research.forEach(item => item.status = 'Ready'); button.disabled = false; button.textContent = 'Run research'; renderResearch(); showToast('AI research completed for 3 sample leads'); }, 1000); });
$('#testEmailForm').addEventListener('submit', event => { event.preventDefault(); const recipient = $('#testRecipient'), subject = $('#testSubject'), status = $('#testStatus'); if (!recipient.validity.valid || !subject.value.trim()) { status.textContent = 'Enter a valid recipient and subject to run the simulated test.'; status.className = 'test-status error'; return; } const button = $('#sendTest'); button.disabled = true; button.textContent = 'Sending simulated test…'; status.textContent = 'Preparing simulated delivery…'; status.className = 'test-status'; setTimeout(() => { button.disabled = false; button.textContent = 'Send test email'; status.textContent = `Simulated test delivered to ${recipient.value}. No real email was sent.`; status.className = 'test-status success'; }, 900); });

renderLeads(); renderActivity(); renderCampaigns(); renderCampaignDetail(); renderResearch();
const initialView = location.hash.slice(1); if (['leads','pipeline','campaigns','insights','settings'].includes(initialView)) setView(initialView);
