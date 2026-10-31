"""Stand-in for `pil --debug-service`: speaks protocol 1 with canned replies.

`demo hello` then `run N` sends "Hello, world!\n" and halts, like PIL's demo.
"""
import json
import sys

state = {'regs': [0] * 8, 'eip': 0x100, 'demo': 'counter', 'sent': False, 'loaded': None}


def reply(seq, ok=True, quit=False, text='', status='ready', output=b''):
    message = {'protocol': 1, 'seq': seq, 'ok': ok, 'quit': quit, 'text': text, 'status': status,
               'guest_output': list(output),
               'state': {'version': '0.35-fake', 'demo': state['demo'], 'registers': state['regs'],
                         'eip': state['eip'], 'flags': 2, 'undefined_flags': 0, 'selectors': [0] * 6,
                         'segments': '', 'breakpoints': [], 'listing': '', 'memory_address': 0x100,
                         'memory': '', 'stack_address': 0, 'stack': '', 'ram_size': 4096, 'cache': '',
                         'pil': '', 'memory_effect': None}}
    sys.stdout.write(json.dumps(message) + '\n')
    sys.stdout.flush()


args = sys.argv[1:]
if '--load' in args:
    state['loaded'] = args[args.index('--load') + 1]
    state['demo'] = 'image'
reply(0, text='PIL debugger connected')
seq = 0
for line in sys.stdin:
    seq += 1
    words = line.split()
    if words == ['demo', 'hello']:
        state.update(demo='hello', eip=0x100, sent=False)
        reply(seq, text='demo hello loaded')
    elif words[:1] == ['run'] and len(words) == 2:
        if state['demo'] == 'loop':
            state['eip'] += 1
            reply(seq, text=f'{words[1]} completed steps; budget', status='budget')
        elif not state['sent']:
            state.update(sent=True, eip=0x138)
            state['regs'][0] = 0x0a
            reply(seq, text='56 completed steps; HLT', status='halt', output=b'Hello, world!\n')
        else:
            reply(seq, text='0 completed steps; HLT', status='halt')
    elif words == ['demo', 'loop']:
        state.update(demo='loop')
        reply(seq, text='demo loop loaded')
    elif words == ['loaded']:
        reply(seq, text=str(state['loaded']))
    elif words == ['quit']:
        reply(seq, quit=True, text='bye')
        break
    else:
        reply(seq, ok=False, text='command is not available in the bounded debugger service; type help',
              status='error')
