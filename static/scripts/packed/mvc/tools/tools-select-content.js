define(["utils/utils","mvc/ui/ui-misc","mvc/ui/ui-tabs","mvc/tools/tools-template"],function(c,e,b,a){var d=Backbone.View.extend({initialize:function(n,h){this.options=h;var g=this;this.setElement("<div/>");this.current="hda";this.button_new=new e.RadioButton.View({value:this.current,data:[{icon:"fa-file-o",label:"Select datasets",value:"hda"},{icon:"fa-files-o",label:"Select a collection",value:"hdca"}],onchange:function(i){g.current=i;g.refresh();g.trigger("change")}});var l=n.content.filterType({src:"hda",extensions:h.extensions});var k=[];for(var j in l){k.push({label:l[j].hid+": "+l[j].name,value:l[j].id})}this.select_datasets=new e.Select.View({multiple:true,data:k,value:k[0]&&k[0].value,onchange:function(){g.trigger("change")}});var m=n.content.filterType({src:"hdca",extensions:h.extensions});var f=[];for(var j in m){f.push({label:m[j].hid+": "+m[j].name,value:m[j].id})}this.select_collection=new e.Select.View({data:f,value:f[0]&&f[0].value,onchange:function(){g.trigger("change")}});this.$el.append(c.wrap(this.button_new.$el));this.$el.append(this.select_datasets.$el);this.$el.append(this.select_collection.$el);if(!this.options.multiple){this.$el.append(a.batchMode())}this.refresh();this.on("change",function(){if(h.onchange){h.onchange(g.value())}})},value:function(k){if(k!==undefined){if(k.values.length>0&&k.values[0]&&k.values[0].src){var j=[];for(var g in k.values){j.push(k.values[g].id)}this.current=k.values[0].src;this.refresh();switch(this.current){case"hda":this.select_datasets.value(j);break;case"hdca":this.select_collection.value(j[0]);break}}}var h=this._select().value();if(!(h instanceof Array)){h=[h]}var f={batch:!this.options.multiple,values:[]};for(var g in h){f.values.push({id:h[g],src:this.current})}return f},validate:function(){return this._select().validate()},refresh:function(){switch(this.current){case"hda":this.select_datasets.$el.fadeIn();this.select_collection.$el.hide();break;case"hdca":this.select_datasets.$el.hide();this.select_collection.$el.fadeIn();break}},_select:function(){switch(this.current){case"hdca":return this.select_collection;default:return this.select_datasets}}});return{View:d}});