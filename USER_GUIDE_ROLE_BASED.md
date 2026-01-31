# CINEAI - Role-Based Video Analysis Usage Guide

## 🎬 What's New?

CINEAI now features **role-based retrieval** that lets you search videos from two different perspectives:

- **🎭 Actor Role**: Find performance moments, emotions, character interactions
- **🎬 Director Role**: Find cinematography techniques, shot compositions, lighting

---

## 🚀 Quick Start

### 1. Installation

#### Backend Setup
```bash
cd backend

# Install dependencies (includes new scene detection library)
pip install -r requirements.txt

# Add your Gemini API key to .env
echo "GEMINI_API_KEY=your_api_key_here" > .env

# Start the backend
python main.py
```

#### Frontend Setup
```bash
cd frontend

# Install dependencies
npm install

# Start the development server
npm run dev
```

### 2. First Upload

1. Open the frontend (usually http://localhost:5173)
2. Click "Upload Video" and select a video file
3. Wait for analysis to complete (~10 minutes for a 1-minute video)
4. Once complete, you can start asking questions!

---

## 🎭 Using Actor Role

### What Actor Role Searches For

- **Content**: What's happening in the scene
- **Objects**: Props, items, people
- **Actions**: What characters are doing
- **Emotions**: Character feelings and expressions
- **Interactions**: Character relationships

### Example Actor Queries

```
✅ "Show me emotional scenes"
✅ "Where is the character angry?"
✅ "Find dialogue moments"
✅ "Show action sequences"
✅ "Find scenes with multiple characters"
✅ "Where are the happy moments?"
✅ "Show me dramatic moments"
✅ "Find quiet, reflective scenes"
```

### What You'll Get

Results include:
- Scene summary
- Number of characters
- Detected emotions and intensity
- Objects in the scene
- Actions being performed
- Timestamp to jump to that moment

### Example Result
```
Found 3 relevant moments:

1. [00:45] - Character sitting alone, looking sad
   1 character(s), emotions: sad

2. [01:23] - Two characters arguing intensely
   2 character(s), emotions: angry

3. [02:10] - Group laughing together
   3 character(s), emotions: happy
```

---

## 🎬 Using Director Role

### What Director Role Searches For

- **Shot Types**: Wide, medium, close-up, extreme close-up
- **Camera Angles**: Eye level, high angle, low angle, bird's eye
- **Lighting**: Natural, artificial, high key, low key, backlit
- **Scene Types**: Indoor vs outdoor
- **Composition**: Technical cinematography

### Example Director Queries

```
✅ "Show me wide angle shots"
✅ "Find low lighting scenes"
✅ "Where are the close-ups?"
✅ "Show high angle shots"
✅ "Find outdoor scenes"
✅ "Show natural lighting"
✅ "Where is backlit lighting used?"
✅ "Find bird's eye view shots"
```

### What You'll Get

Results include:
- Scene summary
- Shot type (wide, medium, close-up, etc.)
- Camera angle (eye level, high, low, etc.)
- Lighting type (natural, artificial, etc.)
- Scene type (indoor/outdoor)
- Timestamp to jump to that moment

### Example Result
```
Found 3 relevant moments:

1. [00:15] - Person walking through forest
   wide shot, eye level, natural, outdoor

2. [01:30] - Character contemplating by window
   medium shot, eye level, natural, indoor

3. [02:45] - Dramatic confrontation
   close-up, low angle, high key, indoor
```

---

## 💡 Pro Tips

### For Best Results

1. **Be Specific**: Instead of "find scenes", say "find emotional scenes" or "find wide shots"

2. **Match Role to Intent**:
   - Looking for technical aspects? → Use Director role
   - Looking for story/performance? → Use Actor role

3. **Use Domain Language**:
   - Director: "wide angle", "low key lighting", "high angle"
   - Actor: "angry", "dialogue", "action", "emotional"

4. **Iterate**: If results aren't perfect, rephrase your query

5. **Switch Roles**: Try the same query in both roles for different perspectives

### Query Examples by Situation

**Planning a Reshoot:**
```
Director: "Show me outdoor scenes with natural lighting"
Director: "Find all wide shots"
```

**Studying Performance:**
```
Actor: "Show me emotional moments"
Actor: "Find dialogue between characters"
```

**Analyzing Cinematography:**
```
Director: "Where are close-ups used?"
Director: "Show me low lighting scenes"
```

**Finding Specific Moments:**
```
Actor: "Where is the character angry?"
Director: "Show me high angle shots"
```

---

## 🎯 Feature Highlights

### Scene Detection

The system automatically detects scene changes in your video:
- Groups similar frames together
- Identifies scene boundaries
- Helps organize search results by scene

### Dual Embeddings

Each frame is analyzed twice:
1. **Technical Analysis** (for Director role)
   - Shot composition
   - Camera work
   - Lighting setup

2. **Content Analysis** (for Actor role)
   - What's happening
   - Who's in the scene
   - Emotional content

This ensures you get the most relevant results for your role!

### Smart Search

- **Semantic Search**: Understands meaning, not just keywords
- **Relevance Scoring**: Best matches appear first
- **Role-Specific Indices**: Separate databases for optimal accuracy

---

## 📊 Understanding Results

### Score Interpretation

- **0.9 - 1.0**: Excellent match
- **0.7 - 0.9**: Good match
- **0.5 - 0.7**: Moderate match
- **< 0.5**: Weak match (still potentially relevant)

### Clicking Timestamps

Results include clickable timestamps:
- Click any timestamp to jump to that moment in the video
- Format: `[MM:SS]`
- Example: `[01:23]` = 1 minute, 23 seconds

---

## ⚡ Performance Notes

### Analysis Time

For a 60-second video:
- Scene detection: ~15 seconds
- Frame extraction: ~5 seconds
- AI analysis: ~7 minutes
- Embedding creation: ~2 minutes
- Database building: ~10 seconds
- **Total**: ~10 minutes

### Query Speed

- Typical query: < 1 second
- First query per video: ~1-2 seconds (loads index)
- Subsequent queries: < 500ms

### Storage Requirements

- Original video: Depends on file size
- Extracted frames: ~60 JPG files per minute of video
- Vector databases: ~10MB per minute of video
- Metadata: ~1MB per minute of video

---

## 🔧 Troubleshooting

### Analysis Takes Too Long

**Normal behavior**: Analysis is intentionally thorough
- Scene detection scans entire video
- Each frame analyzed individually with AI
- Dual embeddings generated for each frame

**If stuck**: Check backend logs for errors

### Poor Search Results

**Solution 1**: Check if you're using the right role
- Technical questions → Director role
- Content questions → Actor role

**Solution 2**: Rephrase your query
- Be more specific
- Use domain-appropriate language

**Solution 3**: Try multiple related queries
- "angry scenes" vs "character emotions"
- "wide shots" vs "wide angle camera"

### "Video Already Analyzed" Message

**Why**: Video was analyzed with old system (pre-role-based)

**Solution**: 
1. Delete old analysis files (optional)
2. Re-upload and re-analyze the video
3. New system will create role-based indices

---

## 📚 Advanced Usage

### Combining Queries

Search for the same moment from different angles:

```
1. Actor: "Show emotional confrontation"
   → Returns: Scene with high emotions

2. Director: "Show close-up shots"
   → Returns: Same scene, but highlights cinematography
```

### Building Shot Lists

Director workflow:
```
1. "Find all wide shots" → Note timestamps
2. "Show close-up shots" → Note timestamps  
3. "Find outdoor scenes" → Note timestamps
4. Create comprehensive shot list
```

### Performance Analysis

Actor workflow:
```
1. "Show all emotional scenes" → Review performance
2. "Find dialogue moments" → Check delivery
3. "Where am I on screen?" → Track presence
4. Compile performance notes
```

---

## 🎓 Best Practices

### Uploading Videos

1. **Supported formats**: MP4, AVI, MOV, MKV, WEBM
2. **Recommended**: 1080p or lower for faster processing
3. **Length**: Works best with videos under 5 minutes
4. **Quality**: Higher quality = better analysis

### Organizing Work

1. **Use descriptive filenames** when uploading
2. **Re-analyze if making significant edits**
3. **Keep notes** on useful timestamps
4. **Export results** for shot lists or reports

### Maximizing Accuracy

1. **Let analysis complete fully** before querying
2. **Use natural language** in queries
3. **Match vocabulary to role** (technical vs descriptive)
4. **Review multiple results** not just the top match

---

## 🌟 Use Cases

### Film Students
- Study cinematography techniques
- Analyze performances
- Create shot breakdowns
- Learn from examples

### Content Creators
- Find B-roll footage quickly
- Locate specific shots
- Review technical quality
- Plan reshoots

### Actors
- Review performance moments
- Find emotional scenes
- Track character arc
- Prepare for auditions

### Directors
- Analyze shot composition
- Review camera work
- Study lighting setups
- Plan cinematography

### Video Editors
- Find specific footage fast
- Locate matching shots
- Review scene continuity
- Build timelines efficiently

---

## 🚦 System Status

### During Analysis

Watch the progress bar:
- **Green**: Making progress
- **Generating frames**: 10% complete
- **Analyzing frames**: 10-80% complete (longest step)
- **Building database**: 80-100% complete

### Ready to Use

When analysis completes:
- Progress shows 100%
- Status: "completed"
- Chat input becomes active
- Role selector appears

---

## 🎯 Quick Reference

### Actor Role Keywords
```
emotions, character, dialogue, action,
performance, scene, story, interaction,
moment, feeling, expression
```

### Director Role Keywords
```
shot, angle, lighting, camera, wide,
close-up, outdoor, indoor, composition,
framing, cinematography, technical
```

### Common Questions

**Q: Can I switch roles mid-conversation?**
A: Yes! Just click the other role button. Previous messages stay the same.

**Q: Do I need to re-analyze for each role?**
A: No! One analysis creates both role indices.

**Q: Which role is better?**
A: Neither! Use the role that matches your question.

**Q: Can I use the same query in both roles?**
A: Yes! You'll get different perspectives on the same content.

---

## 📞 Getting Help

If you encounter issues:

1. **Check the backend logs** for detailed errors
2. **Verify your API key** is correct in `.env`
3. **Ensure video format** is supported
4. **Confirm analysis completed** before querying
5. **Try rephrasing** your query

---

## 🎉 Enjoy!

You now have a powerful tool to explore videos from both performance and technical perspectives. Whether you're an actor studying performances or a director analyzing cinematography, CINEAI helps you find exactly what you're looking for!

Happy analyzing! 🎬🎭
