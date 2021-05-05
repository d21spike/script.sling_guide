from resources.lib.globals import *
from threading import Thread
import xmltodict

class Guide(xbmcgui.WindowXML):

    Monitor = None
    Visible = False
    Player = None
    Service = None
    GuideThread = None
    Active = False

    GuideURL = 'http://192.168.0.110:9999/guide.xml'

    Channels = {}
    GuideSlots = {}
    ClickFocus = None
    CurrentFocus = None
    GuideStart = 0
    GuideStop = 0
    StartTime = 0
    StopTime = 0
    StartChannel = 1
    StopChannel = 10

    #cls is the class that is needed to be instantiated
    def __new__(cls):
        log('::__new__()')
        return super(Guide, cls).__new__(cls, 'window-main.xml', SETTINGS.getAddonInfo('path'))

    def __init__(self):
        log('::__init__()')
        super(Guide, self).__init__()

        self.Monitor = xbmc.Monitor()
        self.Visible = True
        self.Player = xbmc.Player()
        self.Active = True        
            
    def onInit(self):
        log('::onInit()')

        self.initTime()

        self.retrieveGuide()
        while self.Active and not self.Monitor.abortRequested():
            self.updateTimestamps()

            xbmc.sleep(1000)
        log('Aborted')

    def initTime(self):
        log('::initTime()')

        start_minutes = int(datetime.datetime.now().strftime("%M"))
        if start_minutes >= 30:
            self.StartTime = int(time.time()) - ((start_minutes - 30) * 60) - int(datetime.datetime.now().strftime("%S"))
        else:
            self.StartTime = int(time.time()) - (start_minutes * 60) - int(datetime.datetime.now().strftime("%S"))
        self.StopTime = self.StartTime + (120 * 60)
        log('::initTime() Timestamps: Start: %i | Stop: %i' %
            (self.StartTime, self.StopTime))

    def onAction(self, action):
        log('::onAction() %i' % action.getId())

        if action.getId() == ACTION_BKSPACE and self.Visible:
            log('::onAction() Backspace pressed')
            self.close()
            return

        if action.getId() == ACTION_ESCAPE and self.Player.isPlaying() and not self.Visible:
            log('::onAction() Escape pressed')
            self.showEPG()

        if action.getId() == ACTION_UP:
            log('::onAction() Up pressed')
            self.moveUp()

        if action.getId() == ACTION_DOWN:
            log('::onAction() Down pressed')
            self.moveDown()

        if action.getId() == ACTION_LEFT:
            log('::onAction() Left pressed')
            self.moveLeft()

        if action.getId() == ACTION_SWIPE_LEFT:
            log('::onAction() Left swipe')
            self.movePageRight()

        if action.getId() == ACTION_RIGHT:
            log('::onAction() Right pressed')
            self.moveRight()

        if action.getId() == ACTION_SWIPE_RIGHT:
            log('::onAction() Right swipe')
            self.movePageLeft()

        if action.getId() == ACTION_PGUP or action.getId() == ACTION_SWIPE_DOWN:
            log('::onAction() Page Up pressed')
            self.movePageUp()
        
        if action.getId() == ACTION_PGDOWN or action.getId() == ACTION_SWIPE_UP:
            log('::onAction() Page Down pressed')
            self.movePageDown()

        if action.getId() == ACTION_HOME:
            log('::onAction() Home pressed')
            self.movePageHome()

        if action.getId() == ACTION_END:
            log('::onAction() End pressed')
            self.movePageEnd()

        if action.getId() == ACTION_LEFTCLICK:
            log('::onAction() Left Click')
            self.setPlay()

        if action.getId() == ACTION_ENTER:
            log('::onAction() Enter Pressed')
            self.tryPlay()

        if action.getId() == ACTION_RIGHT_CLICK or action.getId() == ACTION_MENU:
            log('::onAction() Menu/Right Click pressed')
            self.tryRecord()
    
    def getControls(self, controlId):
        log('::getControl()')
        control = None
        try:
            control = super(Guide, self).getControl(controlId)
        except Exception:
            if not self.isClosing:
                xbmcgui.Dialog().ok("Error", "Failed to get control", "","")
                self.close()
        return control

    def retrieveGuide(self):
        log('::retrieveGuide()')
        validDB = xbmcvfs.exists(DB_PATH)
        log('::retrieveGuide() DB Exists => %s\rPath: %s' % (str(validDB), DB_PATH))

        if validDB:
            DB = sqlite3.connect(DB_PATH)

            self.Channels = {}
            query = "SELECT DISTINCT Channels.Guid, Channels.name, Channels.thumbnail, Channels.qvt_url, Channels.genre " \
                "FROM Channels " \
                "INNER JOIN Guide on Channels.GUID = Guide.Channel_GUID " \
                "WHERE Channels.Name NOT LIKE '%Sling%' AND Channels.Hidden = 0 " \
                "ORDER BY Channels.Name asc, substr(Channels.Call_Sign, -2) = '-M' desc"

            try:
                cursor = DB.cursor()
                cursor.execute(query)
                dbChannels = cursor.fetchall()
                channel_names = ''
                if dbChannels is not None and len(dbChannels):
                    for row in dbChannels:
                        id = str(row[0])
                        title = str(strip(row[1]).replace("''", "'"))
                        logo = str(row[2])
                        url = str(row[3])
                        genre = str(row[4])
                        if '"%s"' % title not in channel_names:
                            channel_names = '%s,"%s"' % (channel_names, title) if channel_names != '' else '"%s"' % title
                            self.Channels[len(self.Channels) + 1] = {"ID": id, "Name": title, "Logo": logo, "Playlist": url, "Genre": genre}

                        query = "SELECT Guide.Start, Stop, Name, Description, Thumbnail, Genre, Rating FROM Guide " \
                            "WHERE Channel_GUID = '%s' ORDER BY Guide.Start ASC" % id
                        #  AND Guide.Start >= %i AND Stop <= %i

                        try:
                            cursor = DB.cursor()
                            cursor.execute(query)
                            dbGuide = cursor.fetchall()
                            tempGuide = {}
                            if dbGuide is not None and len(dbGuide):
                                for row in dbGuide:
                                    start = row[0]
                                    stop = row[1]
                                    name = strip(row[2])
                                    description = strip(row[3])
                                    thumbnail = strip(row[4])
                                    genre = strip(row[5])
                                    rating = strip(row[6])

                                    if self.GuideStart == 0:
                                        self.GuideStart = start
                                    else:
                                        if self.GuideStart > start:
                                            self.GuideStart = start

                                    if self.GuideStop == 0:
                                        self.GuideStop = stop
                                    else:
                                        if self.GuideStop < stop:
                                            self.GuideStop = stop

                                    tempGuide[start] = {"Start": start, "Stop": stop, "Name": name,
                                                        "Description": description, "Thumbnail": thumbnail, "Genre": genre, "Rating": rating}
                                    # log("::drawGuide() Channel %i:%s Entry %i=>%i %s" % (len(self.Channels), title, start, stop, name))
                            self.Channels[len(self.Channels)]["Guide"] = tempGuide
                        except sqlite3.Error as err:
                            error = '::drawGuide() Failed to retrieve channel %s guide from DB, error => %s\rQuery => %s' % (title, err, query)
                            log(error)
                        except Exception as exc:
                            error = '::drawGuide() Failed to retrieve channel %s guide from DB, exception => %s\rQuery => %s' % (title, exc, query)
                            log(error)
            except sqlite3.Error as err:
                error = '::retrieveGuide() Failed to retrieve channels from DB, error => %s\rQuery => %s' % (err, query)
                log(error)
            except Exception as exc:
                error = '::retrieveGuide() Failed to retrieve channels from DB, exception => %s\rQuery => %s' % (exc, query)
                log(error)

            # log('::retrieveGuide() Channels: \r%s' % json.dumps(channels, indent=4))            
            if len(self.Channels):
                self.drawGuide()                   

    def drawGuide(self):
        log('::drawGuide()')

        # Start X-coordinate is 157 and Y-coordinate is 210
        # Each half hour slot is 276 pixels minus 2 pixels for the gap
        # Total width is 1106
        # Each height is 45

        row = 0
        selected = False
        for channelIndex in range(self.StartChannel, self.StopChannel + 1):
            channel = self.Channels[channelIndex]
            logo = self.getControl(10000 + (1000 * (row + 1)))
            label = self.getControl(10001 + (1000 * (row + 1)))
            logo.setImage(channel["Logo"])
            label.setLabel(str(channelIndex))
            self.GuideSlots[channelIndex] = {}

            noFocus = xbmcvfs.translatePath(os.path.join(IMAGE_PATH, 'button_no_focus.png'))
            focus = xbmcvfs.translatePath(os.path.join(IMAGE_PATH, 'button_focus.png'))
            noSlots = True
            for key in sorted(channel["Guide"]):
                slot = channel["Guide"][key]
                if (self.StartTime <= slot["Start"] < self.StopTime) or (self.StartTime < slot["Stop"] < self.StopTime):
                    log('::drawGuide() Channel: %s Slot => %i' % (channel["Name"], slot["Start"]))
                    noSlots = False

                    startDiff = slot["Start"] - self.StartTime
                    if startDiff > 0:
                        startDiff = startDiff / 60
                    else: 
                        startDiff = 0
                    xCor = 160 + (startDiff * 9.2) - 2
                    yCor = 210 + (row * 50)
                    height = 45
                    if slot["Start"] > self.StartTime:
                        duration = slot["Stop"] - slot["Start"]
                    else:
                        duration = slot["Stop"] - self.StartTime
                    stopOffset = ((duration / 60) * 9.2) -2
                    width = stopOffset
                    if (xCor + stopOffset) > 1263:
                        width = 1263 - xCor
                    label = slot["Name"]
                    if int(width) > 1:
                        log('::drawGuide() Channel: %s Slot: %s Time: %i=>%i Duration: %i Position: (%d, %d) Width: %d' % (channel["Name"], slot["Name"], slot["Start"], slot["Stop"], duration, xCor, yCor, width))
                        button = xbmcgui.ControlButton(x=int(xCor), y=int(yCor), width=int(width), height=height, alignment=6, noFocusTexture=noFocus, focusTexture=focus, label=label)
                    
                    try:
                        self.addControl(button)
                        self.GuideSlots[channelIndex][slot["Start"]] = button.getId()
                        if not selected:
                            self.setFocus(button)
                            selected = True
                            self.showInfo(channelIndex, slot['Start'])
                    except:
                        log('::drawGuide() Channel %s | Control %i: Control already used' % (channel["Name"], button.getId()))
            
            if noSlots:
                log('::drawGuide() Channel: %s no slots' % channel["Name"])

                xCor = 157
                yCor = 210 + (row * 50)
                height = 45
                width = 1106
                label = "Nothing Scheduled"
                button = xbmcgui.ControlButton(x=xCor, y=yCor, width=width, height=height, alignment=6, noFocusTexture=noFocus, focusTexture=focus, label=label)
                self.addControl(button)
                self.GuideSlots[channelIndex][self.StartTime] = button.getId()
            row += 1

    def showInfo(self, channelId, timestamp):
        log('::showInfo()')

        updated = False
        slotThumb = self.getControls(5023)
        slotTitle = self.getControls(5024)
        slotDescription = self.getControls(5025)
        slotTime = self.getControls(5026)
        slotRating = self.getControls(5027)

        channel = self.Channels[channelId]
        for time in channel["Guide"]:
            if time == timestamp:
                info = channel["Guide"][time]
                log('::showInfo() Info \r%s' % json.dumps(info, indent=4))

                slotThumb.setImage(info["Thumbnail"])
                slotTitle.setLabel("[B]" + info["Name"] + "[/B]")
                slotDescription.setLabel(info['Description'][0:130])
                start = datetime.datetime.fromtimestamp(info['Start']).strftime('%H:%M %p')
                stop = datetime.datetime.fromtimestamp(info['Stop']).strftime('%H:%M %p')
                slotTime.setLabel("[B]Start:[/B] " + start + "       [B]Stop:[/B] " + stop)
                slotRating.setLabel("[B]Rating:[/B] " + info["Rating"])
                updated = True

                break
        
        if updated == False:
            noThumb = xbmcvfs.translatePath(os.path.join(IMAGE_PATH, 'no_thumb.png'))
            slotThumb.setImage(noThumb)
            slotTitle.setLabel("")
            slotDescription.setLabel("")
            slotTime.setLabel("")
            slotRating.setLabel()

    def getFocusChannel(self):
        log('::getFocusChannel()')

        currentFocusID = self.getFocusId()
        log('::getFocusChannel() Current Focus ID: %i' % currentFocusID)
        
        focusChannel = 0
        focusTimestamp = 0
        if len(self.GuideSlots):
            for channelId in self.GuideSlots:
                channel = self.GuideSlots[channelId]

                for timestamp in channel:
                    controlId = channel[timestamp]
                    if controlId == currentFocusID:
                        focusChannel = channelId
                        focusTimestamp = timestamp
                        break

                if focusChannel != 0:
                    break
        return focusChannel, focusTimestamp

    def moveUp(self):
        log('::moveUp()')

        if len(self.GuideSlots):
            focusChannel, focusTimestamp = self.getFocusChannel()
            newFocusId = 0
            if (focusChannel - 1) > 0:
                newChannelId = focusChannel - 1
                if newChannelId < self.StartChannel:
                    self.movePageUp()
                    newChannelId = self.StopChannel
                    
                nextChannel = self.GuideSlots[newChannelId]

                slotTimestamp = None
                for timestamp in sorted(nextChannel):
                    newFocusId = nextChannel[timestamp]
                    slotTimestamp = timestamp
                    break
                if newFocusId != 0:
                    self.setFocusId(newFocusId)
                    self.showInfo(newChannelId, slotTimestamp)
        else:
            log('::moveUp() The guide is empty.')

    def moveDown(self):
        log('::moveDown()')

        if len(self.GuideSlots):
            focusChannel, focusTimestamp = self.getFocusChannel()
            newFocusId = 0
            if (focusChannel + 1) <= len(self.Channels):
                newChannelId = focusChannel + 1
                if newChannelId < self.StartChannel:
                    newChannelId = self.StartChannel

                nextChannel = focusChannel
                if newChannelId > self.StopChannel:
                    self.movePageDown()
                    newChannelId = self.StartChannel
                nextChannel = self.GuideSlots[newChannelId]

                slotTimestamp = None
                for timestamp in sorted(nextChannel):
                    newFocusId = nextChannel[timestamp]
                    slotTimestamp = timestamp
                    break
                if newFocusId != 0:
                    self.setFocusId(newFocusId)
                    self.showInfo(newChannelId, slotTimestamp)
        else:
            log('::moveDown() The guide is empty.')

    def moveLeft(self):
        log('::moveLeft()')

        # Proceed only if the guide isn't empty
        if len(self.GuideSlots):
            focusChannel, focusTimestamp = self.getFocusChannel()
            newFocusId = 0
            log('::moveLeft() Current Channel: %i | Current Timestamp: %i' %
                (focusChannel, focusTimestamp))

            # Proceed only if a channel has focus
            if focusChannel != 0:
                channel = self.Channels[focusChannel]
                slot = None

                # Proceed only if a control (slot) has focus
                if focusTimestamp != 0:
                    slot = channel["Guide"][focusTimestamp]
                    log('::moveLeft() Current Focus: %s' %
                        json.dumps(slot, indent=4))

                    # Proceed if a valid slot was found
                    if slot is not None:
                        if slot["Start"] > self.StartTime:
                            nextSlot = False
                            for timestamp in sorted(self.GuideSlots[focusChannel], reverse=True):
                                if nextSlot:
                                    newFocusId = self.GuideSlots[focusChannel][timestamp]
                                    focusTimestamp = timestamp
                                    break

                                if timestamp == focusTimestamp:
                                    nextSlot = True
                        # Slot runs past the current end time, move to next time block
                        else:
                            log('::moveLeft() Time slot at end of block, moving page left')
                            self.movePageLeft()
                    # Hit a nothing a scheduled block, move to next time block
                    else:
                        log('::moveLeft() Unscheduled slot end of block, moving page left')
                        self.movePageLeft()

            if newFocusId != 0:
                self.setFocusId(newFocusId)
                self.showInfo(focusChannel, focusTimestamp)

    def moveRight(self):
        log('::moveRight()')

        # Proceed only if the guide isn't empty
        if len(self.GuideSlots):
            focusChannel, focusTimestamp = self.getFocusChannel()
            newFocusId = 0
            log('::moveRight() Current Channel: %i | Current Timestamp: %i' % (focusChannel, focusTimestamp))
            
            # Proceed only if a channel has focus
            if focusChannel != 0:
                channel = self.Channels[focusChannel]
                slot = None

                # Proceed only if a control (slot) has focus
                if focusTimestamp != 0:
                    slot = channel["Guide"][focusTimestamp]
                    log('::moveRight() Current Focus: %s' % json.dumps(slot, indent=4))

                    # Proceed if a valid slot was found
                    if slot is not None:
                        if slot["Stop"] < self.StopTime:
                            nextSlot = False
                            for timestamp in sorted(self.GuideSlots[focusChannel]):
                                if nextSlot:
                                    newFocusId = self.GuideSlots[focusChannel][timestamp]
                                    focusTimestamp = timestamp
                                    break

                                if timestamp == focusTimestamp:
                                    nextSlot = True
                        # Slot runs past the current end time, move to next time block
                        else:
                            log('::moveRight() Time slot at end of block, moving page right')
                            self.movePageRight()
                    # Hit a nothing a scheduled block, move to next time block
                    else:
                        log('::moveRight() Unscheduled slot end of block, moving page right')
                        self.movePageRight()

            if newFocusId != 0:
                self.setFocusId(newFocusId)
                self.showInfo(focusChannel, focusTimestamp)

    def movePageUp(self):
        log('::movePageUp()')
        self.removeSlots()

        log('::movePageUp() Current Start: %i Current Stop: %i' % (self.StartChannel, self.StopChannel))
        if (self.StartChannel - 10) > 0:
            self.StartChannel -= 10
            self.StopChannel -= 10
        else:
            self.StartChannel = 1
            self.StopChannel = len(self.Channels) + 1


        log('::movePageUp() New Start: %i New Stop: %i' % (self.StartChannel, self.StopChannel))
        self.drawGuide()

    def movePageDown(self):
        log('::movePageDown()')
        self.removeSlots()
        
        log('::movePageDown() Current Start: %i Current Stop: %i' % (self.StartChannel, self.StopChannel))
        if (self.StartChannel + 10) < len(self.Channels):
            self.StartChannel += 10
            self.StopChannel += 10
        else:
            self.StartChannel = len(self.Channels) - 9
            self.StopChannel = len(self.Channels)

        log('::movePageDown() New Start: %i New Stop: %i' % (self.StartChannel, self.StopChannel))
        self.drawGuide()  

    def movePageLeft(self):
        log('::movePageLeft()')

        # self.StartTime = int(time.time()) - ((start_minutes - 30) * 60) - int(datetime.datetime.now().strftime("%S"))
        # self.StartTime = int(time.time()) - (start_minutes * 60) - int(datetime.datetime.now().strftime("%S"))
        # self.StopTime = self.StartTime + (120 * 60)
        if self.GuideStart < self.StartTime:
            self.StopTime = self.StartTime
            self.StartTime = self.StartTime - (120 * 60)
            log("::movePageLeft() New page Start: %i | Stop: %i")

            self.updateTimestamps()
            self.removeSlots()
            self.drawGuide()
        else:
            log("::movePageLeft() There's no more pages to the left")

    def movePageRight(self):
        log('::movePageRight()')

        if self.GuideStop > self.StopTime:
            self.StartTime = self.StopTime
            self.StopTime = self.StopTime + (120 * 60)
            log("::movePageRight() New page Start: %i | Stop: %i")

            self.updateTimestamps()
            self.removeSlots()
            self.drawGuide()
        else:
            log("::movePageRight() There's no more pages to the left")


    def movePageHome(self):
        log('::movePageHome()')
        self.removeSlots()
        self.initTime()

        log('::movePageHome() Current Start: %i Current Stop: %i' % (self.StartChannel, self.StopChannel))
        
        self.StartChannel = 1
        if len(self.Channels) >= 10:
            self.StopChannel = 10
        else:
            self.StopChannel = len(self.Channels) + 1

        log('::movePageHome() New Start: %i New Stop: %i' % (self.StartChannel, self.StopChannel))
        self.drawGuide()

    def movePageEnd(self):
        log('::movePageEnd()')
        self.removeSlots()

        log('::movePageEnd() Current Start: %i Current Stop: %i' % (self.StartChannel, self.StopChannel))
        
        self.StartChannel = len(self.Channels) - 9
        if self.StartChannel < 1:
            self.StartChannel = 1
            self.StopChannel = len(self.Channels)
        else:
            self.StopChannel = len(self.Channels)

        log('::movePageEnd() New Start: %i New Stop: %i' % (self.StartChannel, self.StopChannel))
        self.drawGuide()

    def removeSlots(self):
        log('::removeSlots() Channel: %i through %i' % (self.StartChannel, self.StopChannel + 1))
        controlList = []
        for channelIndex in range(self.StartChannel, self.StopChannel + 1):
            try:
                slots = self.GuideSlots[channelIndex]
            except:
                log('::removeSlots() Channel: %i failed to get slots' % channelIndex)
                slots = None
            if slots is not None:
                for slot in slots:
                    controlId = slots[slot]
                    control = self.getControls(controlId)
                    controlList.append(control)
            self.GuideSlots[channelIndex] = {}
        self.removeControls(controlList)
                        
    def updateTimestamps(self):
        log('::updateTimestamps()')
        timeLabel = self.getControls(5003)
        while timeLabel is None:
            timeLabel = self.getControls(5003)
        
        displayTime = datetime.datetime.fromtimestamp(self.StartTime)
        timeLabel.setLabel(displayTime.strftime("%b %d, %Y\n%I:%M:%S %p"))

        for increment in range(0, 4):
            labelTime = datetime.datetime.fromtimestamp(self.StartTime + (1800 * increment))
            timeLabel = self.getControl(5018 + increment)
            timeLabel.setLabel(labelTime.strftime("%a %I:%M %p"))

        posLine = self.getControl(5022)
        posY = 168
        if self.StartTime <= int(time.time()) <= self.StopTime:
            startX = 154
            offset = ((int(time.time()) - self.StartTime) / 60) * 9.2
                        
            posLine.setPosition(startX + int(offset), posY)
        elif self.StopTime < int(time.time()):
            posLine.setPosition(1262, posY)
        else:
            posLine.setPosition(154, posY)

    def setPlay(self):
        log('::setPlay()')

        selectedFocus = self.getFocusId()
        if selectedFocus != self.ClickFocus:
            self.ClickFocus = selectedFocus

            focusChannel, focusTimestamp = self.getFocusChannel()
            self.showInfo(focusChannel, focusTimestamp)
        else:
            self.tryPlay()
    
    def tryPlay(self):
        log('::tryPlay()')

        focusChannel, focusTimestamp = self.getFocusChannel()
        if focusChannel != 0:
            if focusTimestamp != 0:
                log('::tryPlay() Examining Channel: %i | Timestamp: %i' % (focusChannel, focusTimestamp))

                channel = self.Channels[focusChannel]
                slot = channel["Guide"][focusTimestamp]
                if slot is not None:
                    if slot["Start"] <= int(time.time()) < slot["Stop"]:
                        playURL = 'plugin://plugin.video.sling/?mode=play&url=%s&name=%s' % (channel["Playlist"], slot["Name"])
                        xbmc.executeJSONRPC('{"jsonrpc":"2.0","method":"Player.Open","params":{"item":{"file":"%s"}},"id":"1"}' % playURL)
                        self.removeSlots()
            else:
                log('::tryPlay() Unscheduled program cannot play.')

    def tryRecord(self):
        log('::tryRecord()')

        focusChannel, focusTimestamp = self.getFocusChannel()
        if focusChannel != 0:
            if focusTimestamp != 0:
                log('::tryPlay() Examining Channel: %i | Timestamp: %i' %
                    (focusChannel, focusTimestamp))

                channel = self.Channels[focusChannel]
                slot = channel["Guide"][focusTimestamp]
                if slot is not None:
                    if slot["Stop"] > int(time.time()):
                        record = xbmcgui.Dialog().yesno("Set Record", "Would you like to record %s on %s @ %s?" % ( slot["Name"], channel["Name"], datetime.datetime.fromtimestamp(slot["Start"]).strftime('%I:%M %p')))
                        log('::onAction() Dialog result %s' % record)

                        if record:
                            recURL = 'plugin://plugin.video.sling/?mode=tryRecord&channel=%s&start=%s' % (channel["ID"], slot["Start"])
                            xbmc.executebuiltin('RunPlugin(%s)' % recURL)
                    else:
                        message = "Past program, cannot record."
                        log("::tryRecord() %s" % message)
                        try:
                            xbmcgui.Dialog().notification(ADDON_NAME, message, ICON, 1000, False)
                        except:
                            xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (ADDON_NAME, message, 1000, ICON))
            else:
                message = "Unscheduled program cannot record."
                log("::tryRecord() %s" % message)
                try:
                    xbmcgui.Dialog().notification(ADDON_NAME, message, ICON, 1000, False)
                except:
                    xbmc.executebuiltin("Notification(%s, %s, %d, %s)" % (ADDON_NAME, message, 1000, ICON))
    
    def showEPG(self):
        log('::showEPG()')

    def close(self):
        log('::close()')
        self.Active = False
        super(Guide, self).close()
