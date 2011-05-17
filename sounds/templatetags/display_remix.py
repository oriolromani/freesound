'''
Created on May 6, 2011

@author: stelios
'''
from __future__ import absolute_import, division
#avoid namespace clash with 'tags' templatetag
from django import template
import json
from random import randint

register = template.Library()
@register.inclusion_tag('sounds/display_remix.html', takes_context=True)

def display_remix(context, sound, objectlist):
    
    nodes = []
    links = []
    tempList = []

    # get position in queryset related to ids
    for idx,val in enumerate(objectlist):
        print(val.id)
        tempList.append({'id': val.id, 'pos': idx})
            
    for idx,val in enumerate(objectlist):
        nodes.append({
                      'nodeName':val.original_filename,
                      'group':1,
                      'id':val.id,
                      'color': "rgb" + random_color(),
                      'pos':idx,
                      'username': val.user.username
                      })
        
        # since we go forward in time, if a sound has sources you can assign its sources
        # the target will always be the current object
        for src in val.sources.all():
            links.append({
                          'source': str([t['pos'] for t in tempList if t['id']==src.id]).strip('[,]'),
                          'source_id': src.id, 
                          'target': idx,
                          'target_id': val.id,
                          'value': 1
                          })
        
            
    return  { 'data' :  json.dumps({
                                    'nodes' : nodes,
                                    'links' : links,
                                    'length': len(objectlist)
                                    }) }

# generates shades of green
def random_color():
    greenval = randint(100, 255)
    redval = randint(20,(greenval - 60))
    blueval = randint((redval - 20), (redval + 20))
    color = (redval, greenval, blueval)

    return str(color)
    
    