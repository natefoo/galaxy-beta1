(function(){var b=Handlebars.template,a=Handlebars.templates=Handlebars.templates||{};a["template-history-failedMetaData"]=b(function(g,m,f,l,k){f=f||g.helpers;var c,i,o=this,h="function",n=f.blockHelperMissing,j=this.escapeExpression;function e(t,s){var q="",r,p;q+="\n";p=f.local;if(p){r=p.call(t,{hash:{},inverse:o.noop,fn:o.program(2,d,s)})}else{r=t.local;r=typeof r===h?r():r}if(!f.local){r=n.call(t,r,{hash:{},inverse:o.noop,fn:o.program(2,d,s)})}if(r||r===0){q+=r}q+='\nYou may be able to <a href="';r=t.urls;r=r==null||r===false?r:r.edit;r=typeof r===h?r():r;q+=j(r)+'" target="galaxy_main">set it manually or retry auto-detection</a>.\n';return q}function d(q,p){return"An error occurred setting the metadata for this dataset."}i=f.warningmessagesmall;if(i){c=i.call(m,{hash:{},inverse:o.noop,fn:o.program(1,e,k)})}else{c=m.warningmessagesmall;c=typeof c===h?c():c}if(!f.warningmessagesmall){c=n.call(m,c,{hash:{},inverse:o.noop,fn:o.program(1,e,k)})}if(c||c===0){return c}else{return""}})})();