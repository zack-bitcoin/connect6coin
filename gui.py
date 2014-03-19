from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer
import string,cgi,time, json, random, copy, pickle, os, config
import blockchain, state_library, connect6
import pybitcointools as pt
win_list=['game_name', 'id']
spend_list=connect6.spend_list
def spend(amount, pubkey, privkey, to_pubkey, state):
    amount=int(amount*(10**5))
    tx={'type':'spend', 'id':pubkey, 'amount':amount, 'to':to_pubkey}
    easy_add_transaction(tx, spend_list, privkey, state)
def wingame(game_name, pubkey, privkey, state):
    tx={'type':'winGame', 'game_name':game_name, 'id':pubkey}
    easy_add_transaction(tx, win_list, privkey, state)
def newgame(opponent, name, pubkey_mine, privkey, state, size=19, amount=0):
    try:
        amount=int(float(amount)*(10**5))
    except:
        amount=0
    try:
        size=int(size)
    except:
        size=19
    amount=int(amount)
    print('NEWGAME')
    tx={'type':'newGame', 'game_name':name, 'id':pubkey_mine, 'pubkey_white':opponent, 'pubkey_black':pubkey_mine, 'whos_turn':'black', 'time':5, 'white':[], 'black':[], 'size':size, 'amount':amount}
    easy_add_transaction(tx, connect6.newgame_sig_list, privkey, state)
def move(game_name, location, pubkey, privkey, state):
    board=state[game_name]
    tx_orig={'type':'nextTurn', 'id':pubkey, 'game_name':game_name, 'where':location, 'move_number':board['move_number']}#+len(game_txs)}
    easy_add_transaction(tx_orig, connect6.nextturn_sig_list, privkey, state)
def easy_add_transaction(tx_orig, sign_over, privkey, state):
    tx=copy.deepcopy(tx_orig)
    pubkey=pt.privtopub(privkey)
    if pubkey not in state or 'count' not in state[pubkey]:
        tx['count']=1
    else:
        tx['count']=state[pubkey]['count']
    txs=blockchain.load_transactions()
    my_txs=filter(lambda x: x['id']==pubkey, txs)
    tx['signature']=pt.ecdsa_sign(connect6.message2signObject(tx, sign_over), privkey)
    if blockchain.add_transaction(tx):
        blockchain.pushtx(tx, config.peers_list)
        return True
    if 'move_number' in tx:
        for i in range(10):
            tx['move_number']+=1
            tx['signature']=pt.ecdsa_sign(connect6.message2signObject(tx, sign_over), privkey)
            if blockchain.add_transaction(tx):
                blockchain.pushtx(tx, config.peers_list)
                return True
    print('SOMETHING IS BROKEN')
    return False
def fs2dic(fs):
    dic={}
    for i in fs.keys():
        a=fs.getlist(i)
        if len(a)>0:
            dic[i]=fs.getlist(i)[0]
        else:
            dic[i]=""
    return dic
submit_form='''
<form name="first" action="{}" method="{}">
<input type="submit" value="{}">{}
</form> {}
'''
active_games=[]
def easyForm(link, button_says, moreHtml='', typee='post'):
    a=submit_form.format(link, '{}', button_says, moreHtml, "{}")
    if typee=='get':
        return a.format('get', '{}')
    else:
        return a.format('post', '{}')
linkHome = easyForm('/', 'HOME', '', 'get')

def dot_spot(s, i, j):#the black dots that help for counting out where on the board you are playing. They only show up on board sizes 9, 13, and 19.
    sp=[3,9,15]
    if s==19 and i in sp and j in sp:#if board is size 19
        return True
    sp=[2,6]
    if s==9 and i in sp and j in sp:#if board is size 9
        return True
    sp=[2,10]
    if s==13 and ((i in sp and j in sp) or (j==6 and i==6)):#if board is size 13
        return True
def board_spot(j, i, not_whos_turn_pubkey, whos_turn_pubkey, pubkey, board, privkey):
    s=board['size']#usually 19
    out='{}'
    def pic(x):
        return hex2htmlPicture(x, board_size/19)
    if [j, i] in board['white']:
        if board['whos_turn']=='black' and ([j, i] == board['white'][-1] or [j, i] == board['white'][-2]):
            out=out.format(pic(white_dot_txt))
        else:
            out=out.format(pic(white_txt))
    elif [j, i] in board['black']:
        if board['whos_turn']=='white' and ([j, i] == board['black'][-1] or [j, i] == board['black'][-2]):
            out=out.format(pic(black_dot_txt))
        else:
            out=out.format(pic(black_txt))
    else:
        img=empty_txt
        if dot_spot(s, i, j):
            img=dot_txt
        if True:
            out=out.format('''<form style='display:inline;\n margin:0;\n padding:0;' name="play_a_move" action="/game" method="POST"><input type="image" src="{}" name="move" height="{}"><input type="hidden" name="move" value="{},{}"><input type="hidden" name="game" value="{}"><input type="hidden" name="privkey" value="{}"></form>{}'''.format(txt2src(img), str(board_size/19), str(j), str(i), board['game_name'], privkey,'{}'))
        else:
            out=out.format(hex2htmlPicture(img))
    return out
    
def board(out, state, game, privkey):
    board=state[game]
    s=board['size']
    pubkey=pt.privtopub(privkey)
    if board['whos_turn']=='white':
        whos_turn_pubkey=board['pubkey_white']
        not_whos_turn_pubkey=board['pubkey_black']
    else:
        whos_turn_pubkey=board['pubkey_black']
        not_whos_turn_pubkey=board['pubkey_white']
    for j in range(s):
        out=out.format('<br>{}')
        for i in range(s):
            out=out.format(board_spot(j, i, not_whos_turn_pubkey, whos_turn_pubkey, pubkey, board, privkey))
    return out
def page1(default_brainwallet=''):
    out=empty_page
    out=out.format(easyForm('/home', 'Play Go!', '<input type="text" name="BrainWallet" value="{}">'.format(default_brainwallet)))
    return out.format('')
def home(dic):
    if 'BrainWallet' in dic:
        dic['privkey']=pt.sha256(dic['BrainWallet'])
    elif 'privkey' not in dic:
        return "<p>You didn't type in your brain wallet.</p>"
    privkey=dic['privkey']
    pubkey=pt.privtopub(dic['privkey'])
    def clean_state():
        transactions=blockchain.load_transactions()
        state=state_library.current_state()
        a=blockchain.verify_transactions(transactions, state)
        print('a: ' +str(a))
        return a['newstate']
    state=clean_state()
    if 'do' in dic.keys():
        if dic['do']=='newGame':
            newgame(dic['partner'], dic['game'], pubkey, privkey, state, dic['size'])
            active_games.append(dic['game'])
        if dic['do']=='joinGame':
            active_games.append(dic['game'])
        if dic['do']=='spend':
            try:
                spend(float(dic['amount']), pubkey, privkey, dic['to'], state)
            except:
                pass
        state=clean_state()
    out=empty_page
    out=out.format('<p>your address is: ' +str(pubkey)+'</p>{}')
    print('state: ' +str(state))
    out=out.format('<p>current block is: ' +str(state['length'])+'</p>{}')
    if pubkey not in state:
        state[pubkey]={'amount':0}
    if 'amount' not in state[pubkey]:
        state[pubkey]['amount']=0
    out=out.format('<p>current balance is: ' +str(state[pubkey]['amount']/100000.0)+'</p>{}')        
    if state[pubkey]['amount']>0:
        out=out.format(easyForm('/home', 'spend money', '''
        <input type="hidden" name="do" value="spend">
        <input type="text" name="to" value="address to give to">
        <input type="text" name="amount" value="amount to spend">
        <input type="hidden" name="privkey" value="{}">'''.format(privkey)))    
    s=easyForm('/home', 'Refresh', '''    <input type="hidden" name="privkey" value="{}">'''.format(privkey))
    out=out.format(s)
    out=out.format("<p>You are currently watching these games: {}</p>{}".format(str(active_games),"{}"))
    out=out.format(easyForm('/game', 'Play games', '''<input type="hidden" name="privkey" value="{}">'''.format(privkey)))

    out=out.format(easyForm('/home', 'Join Game', '''
    <input type="hidden" name="do" value="joinGame">
    <input type="hidden" name="privkey" value="{}">
    <input type="text" name="game" value="unique game name">
    '''.format(privkey)))
    out=out.format(easyForm('/home', 'New Game', '''
    <input type="hidden" name="do" value="newGame">
    <input type="hidden" name="privkey" value="{}">
    <input type="text" name="game" value="unique game name">
    <input type="text" name="partner" value="put your partners address here.">
    <input type="text" name="size" value="board size (9, 13, 19 are popular)">
    '''.format(privkey)))
    return out
    
def game(dic):
    if 'BrainWallet' in dic:
        dic['privkey']=pt.sha256(dic['BrainWallet'])
    privkey=dic['privkey']
    pubkey=pt.privtopub(dic['privkey'])
    def clean_state():
        transactions=blockchain.load_transactions()
        state=state_library.current_state()
        return blockchain.verify_transactions(transactions, state)['newstate']
    state=clean_state()
    if 'do' in dic.keys():
        if dic['do']=='winGame':
            wingame(dic['game'], pubkey, privkey, state)
        if dic['do']=='deleteGame':
            active_games.remove(dic['game'])
        state=clean_state()
    if 'move' in dic.keys():
        string=dic['move'].split(',')
        i=int(string[0])
        j=int(string[1])
        move(dic['game'], [i, j], pubkey, privkey, state)
        state=clean_state()
    out=empty_page
    out=out.format('<p>your address is: ' +str(pubkey)+'</p>{}')
    print('state: ' +str(state))
    out=out.format('<p>current block is: ' +str(state['length'])+'</p>{}')
    if pubkey not in state:
        state[pubkey]={'amount':0}
    if 'amount' not in state[pubkey]:
        state[pubkey]['amount']=0
    out=out.format('<p>current balance is: ' +str(state[pubkey]['amount']/100000.0)+'</p>{}')        
    s=easyForm('/game', 'refresh', '''    <input type="hidden" name="privkey" value="{}">'''.format(privkey))
    out=out.format(s)
    s=easyForm('/home', 'main menu', '''    <input type="hidden" name="privkey" value="{}">'''.format(privkey))
    out=out.format(s)
    for game in active_games:
        out=out.format("<h1>"+str(game)+"</h1>{}")
        if game in state:
            out=out.format('<h1>Timer: ' + str(state[game]['last_move_time']+state[game]['time']-state['length'])+' </h1>{}')
        if game in state.keys():
            in_last_block=state[game]
            out=board(out, state, game, privkey)
            out=out.format(easyForm('/game', 'win this game', '''
            <input type="hidden" name="do" value="winGame">
            <input type="hidden" name="privkey" value="{}">
            <input type="hidden" name="game"  value="{}">'''.format(privkey, game)))
            out=out.format(easyForm('/game', 'leave this game', '''
            <input type="hidden" name="do" value="deleteGame">
            <input type="hidden" name="privkey" value="{}">
            <input type="hidden" name="game"  value="{}">'''.format(privkey, game)))
        else:
            out=out.format("<p>this game does not yet exist</p>{}")
            out=out.format(easyForm('/game', 'delete this game', '''
            <input type="hidden" name="do" value="deleteGame">
            <input type="hidden" name="privkey" value="{}">
            <input type="hidden" name="game"  value="{}">'''.format(privkey,game)))
    return out
def hex2htmlPicture(string, size):
    return '<img height="{}" src="data:image/png;base64,{}">{}'.format(str(size), string, '{}')
#def file2hexPicture(fil):
#    return image64.convert(fil)
#def file2htmlPicture(fil):
#    return hex2htmlPicture(file2hexPicture(fil))
def newline():
    return '''<br />
{}'''
empty_page='''<html><head></head><body>{}</body></html>'''
initial_db={}
database='tags.db'
board_size=500
#piece_size=board_size/19
dot_txt="iVBORw0KGgoAAAANSUhEUgAAAAkAAAAJCAIAAABv85FHAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3gITFCMP6bUdsgAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAAAuSURBVAjXY/S448EAAztUdiBzmRhwA+LkdqjsgJOEASPccrgOuAjCTIgQNdwJAJ24Duf6+IShAAAAAElFTkSuQmCC"
empty_txt="iVBORw0KGgoAAAANSUhEUgAAAAkAAAAJCAIAAABv85FHAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3gITDyIL57CkewAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAAAfSURBVAjXY/S448EAAztUdiBzmRhwA3Ll8AFGOrsFAO/zCOeJq9qTAAAAAElFTkSuQmCC"
white_txt="iVBORw0KGgoAAAANSUhEUgAAAAkAAAAJCAIAAABv85FHAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3gITDyM1P8qIkQAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABASURBVAjXY/S448HAwMDAwLBdeTuE4XnXE8Jg8Ljj8R8b8LjjwcSAGzD+//8flxw+fXjlEK5CBZ53PfG6BY//ALQ0JoSAn9HtAAAAAElFTkSuQmCC"
black_txt="iVBORw0KGgoAAAANSUhEUgAAAAkAAAAJCAIAAABv85FHAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3gITDyMEbhSIqwAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAAApSURBVAjXY/S448HAwMDAwLBDZQeEARdBYqECjzseTAx0BmS6hRGP/wCVjQ6PyfnLuwAAAABJRU5ErkJggg=="
white_dot_txt="iVBORw0KGgoAAAANSUhEUgAAAAkAAAAJCAIAAABv85FHAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3gMRDzYJsHnzOQAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABNSURBVAjXY/S448HAwMDAwLBdeTuE4XnXE8Jg8Ljj8R8b8LjjwcSAGzD+//8fzvnGyMiFxGVCloCT6HIQHSj6EK5ClfC864nXLXj8BwCL4jGMEWASqAAAAABJRU5ErkJggg=="
black_dot_txt="iVBORw0KGgoAAAANSUhEUgAAAAkAAAAJCAIAAABv85FHAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3gMRDzkkcj6zgwAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAAAzSURBVAjXY/S448HAwMDAwLBDZQeEARdBYqECjzseTAxEgq+oXEZMCW5i9JHrFkY8/gMACuoRehB1LRMAAAAASUVORK5CYII="
half_white_txt='iVBORw0KGgoAAAANSUhEUgAAAAkAAAAJCAIAAABv85FHAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3gMCFDo4H80I7wAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABTSURBVAjXY/S448HAwMDAwBAiG/Jj4Q+OeI41j9dARFggogxIAMJd83gNEwNuwISmCVk3y4+FP5CFkLksHPEcyBLIXCa4q9AAAbewQJQg+wRuEgBisR8X0r+9ngAAAABJRU5ErkJggg=='
half_black_txt='iVBORw0KGgoAAAANSUhEUgAAAAkAAAAJCAIAAABv85FHAAAACXBIWXMAAAsTAAALEwEAmpwYAAAAB3RJTUUH3gMCFQAdcKJo5gAAABl0RVh0Q29tbWVudABDcmVhdGVkIHdpdGggR0lNUFeBDhcAAABbSURBVAjXY/S448HAwMDAwLBn6p4//X9YCllcsl0gIiwQUQYkAOG6ZLswMeAGzA+YH8A5/078Y7KEqr53+h4ebQyMLIUscA7ELXAuE9xVaICAW1ggSpB9AjcJAJjWHSoSD4gAAAAAAElFTkSuQmCC'
def txt2src(txt):
    return "data:image/png;base64,"+txt
def fs_load():
    try:
        out=pickle.load(open(database, 'rb'))
        return out
    except:
        fs_save(initial_db)
        return pickle.load(open(database, 'rb'))      
def fs_save(dic):
    pickle.dump(dic, open(database, 'wb'))
class MyHandler(BaseHTTPRequestHandler):
   def do_GET(self):
      try:
         if self.path == '/' :    
#            page = make_index( '.' )
            self.send_response(200)
            self.send_header('Content-type',    'text/html')
            self.end_headers()
            self.wfile.write(page1(default_brain))
            return    
         else : # default: just send the file    
            filepath = self.path[1:] # remove leading '/'    
            if [].count(filepath)>0:
#               f = open( os.path.join(CWD, filepath), 'rb' )
                 #note that this potentially makes every file on your computer readable bny the internet
               self.send_response(200)
               self.send_header('Content-type',    'application/octet-stream')
               self.end_headers()
               self.wfile.write(f.read())
               f.close()
            else:
               self.send_response(200)
               self.send_header('Content-type',    'text/html')
               self.end_headers()
               self.wfile.write("<h5>Don't do that</h5>")
            return
         return # be sure not to fall into "except:" clause ?      
      except IOError as e :  
             # debug    
         print e
         self.send_error(404,'File Not Found: %s' % self.path)
   def do_POST(self):
            print("path: " + str(self.path))
            ctype, pdict = cgi.parse_header(self.headers.getheader('content-type'))    
            print(ctype)
            if ctype == 'multipart/form-data' or ctype=='application/x-www-form-urlencoded':    
               fs = cgi.FieldStorage( fp = self.rfile,
                                      headers = self.headers, # headers_,
                                      environ={ 'REQUEST_METHOD':'POST' })
            else: raise Exception("Unexpected POST request")
            self.send_response(200)
            self.end_headers()
            dic=fs2dic(fs)
            jan_script='''
<head><script>
function refreshPage () {
//save y position
localStorage.scrollTop = window.scrollY
// no reload instead posting a hidden form
document.getElementsByName("first")[0].submit()
}

window.onload = function () {

//setting position if available
if(localStorage.scrollTop != undefined) {
window.scrollTo(0, localStorage.scrollTop);    
}
//refresh loop
setTimeout(refreshPage, 3000);
}
</script></head>
'''
            if self.path=='/home':
                self.wfile.write(home(dic))
            if self.path=='/game':
                   self.wfile.write(game(dic).replace('<head></head>', jan_script))
            else:
                print('ERROR: path {} is not programmed'.format(str(self.path)))
default_brain=''
def main(PORT, brain_wallet):
    global default_brain
    default_brain=brain_wallet
    try:
        server = HTTPServer(('', PORT), MyHandler)
        print 'started httpserver...'
        server.serve_forever()
    except KeyboardInterrupt:
        print '^C received, shutting down server'
        server.socket.close()
if __name__ == '__main__':
    main(config.gui_port, config.brain_wallet)




