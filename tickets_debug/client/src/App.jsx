import { useState, useEffect, useMemo } from 'react';
import axios from 'axios';

function App() {
  const [tickets, setTickets] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [activeTab, setActiveTab] = useState('tickets'); // 'tickets' or 'files'
  
  // File browser state
  const [fileStructure, setFileStructure] = useState(null);
  const [fileContent, setFileContent] = useState(null);
  const [selectedFile, setSelectedFile] = useState(null);
  const [fileLoading, setFileLoading] = useState(false);
  const [fileError, setFileError] = useState(null);

  const [filters, setFilters] = useState({
    status: 'all',
    assignee: 'all',
  });

  const fetchTickets = async () => {
    setLoading(true);
    setError(null);
    try {
      // Add timestamp to prevent caching
      const res = await axios.get(`/api/tickets?t=${new Date().getTime()}`);
      // Add null checks to prevent errors
      if (res && res.data) {
        setTickets(Array.isArray(res.data) ? res.data : []);
      } else {
        setTickets([]);
        setError('Invalid response from server');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch tickets');
      setTickets([]);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchTickets();
  }, []);

  const fetchFileStructure = async () => {
    setFileLoading(true);
    setFileError(null);
    try {
      const res = await axios.get(`/api/files/structure?t=${new Date().getTime()}`);
      // Add null checks to prevent errors
      if (res && res.data && res.data.structure) {
        setFileStructure(res.data.structure);
      } else {
        setFileStructure([]);
        setFileError('Invalid response structure from server');
      }
    } catch (err) {
      setFileError(err.response?.data?.error || err.message || 'Failed to fetch file structure');
      setFileStructure(null);
      console.error('File structure error:', err);
    } finally {
      setFileLoading(false);
    }
  };

  const fetchFileContent = async (filePath) => {
    setFileLoading(true);
    setFileError(null);
    setSelectedFile(filePath);
    try {
      const res = await axios.get(`/api/files/content?path=${encodeURIComponent(filePath)}&t=${new Date().getTime()}`);
      // Add null checks to prevent errors
      if (res && res.data) {
        setFileContent(res.data);
      } else {
        setFileContent(null);
        setFileError('Invalid response from server');
      }
    } catch (err) {
      setFileError(err.response?.data?.error || err.message || 'Failed to fetch file content');
      setFileContent(null);
    } finally {
      setFileLoading(false);
    }
  };

  useEffect(() => {
    if (activeTab === 'files') {
      fetchFileStructure();
    }
  }, [activeTab]);

  const assignees = useMemo(() => {
    const set = new Set(tickets.map(t => t.assigned_to).filter(Boolean));
    return Array.from(set);
  }, [tickets]);

  // Helper to normalize IDs for comparison (handles ObjectId, string, etc.)
  // Helper to normalize IDs for comparison (handles ObjectId, string, etc.)
  const normalizeId = (id) => {
    if (!id) return null;
    // If it's an object with $oid or toString, extract the string
    if (typeof id === 'object') {
      if (id.$oid) return String(id.$oid);
      if (id.toString) return String(id.toString());
      return null;
    }
    return String(id);
  };

  const { groupedTickets, orphans } = useMemo(() => {
    const epics = tickets.filter(t => t.type === 'epic');
    const stories = tickets.filter(t => t.type === 'story');
    
    // Map stories to epics using parent_id
    const epicMap = epics.map(epic => {
       const epicId = normalizeId(epic.id || epic._id);
       // Look for parent_id in stories matching the Epic's ID
       const childStories = stories.filter(story => {
          const storyParentId = normalizeId(story.parent_id);
          return storyParentId && epicId && storyParentId === epicId;
       });
       return { ...epic, children: childStories };
    });

    // Identify orphans: Stories that match NO epic in the map
    const allChildIds = new Set(epicMap.flatMap(e => e.children.map(c => normalizeId(c.id || c._id))));
    // An orphan is a story that is NOT in any child list found above
    const orphanStories = stories.filter(s => {
        const id = normalizeId(s.id || s._id);
        return id && !allChildIds.has(id);
    });

    return { groupedTickets: epicMap, orphans: orphanStories };

  }, [tickets]);

  const filterTicket = (t) => {
      if (filters.status !== 'all' && t.status !== filters.status) return false;
      if (filters.assignee !== 'all' && t.assigned_to !== filters.assignee) return false;
      return true;
  };

  const filteredGroups = useMemo(() => {
      return groupedTickets.map(epic => ({
          ...epic,
          children: epic.children.filter(filterTicket)
      })).filter(epic => filterTicket(epic) || epic.children.length > 0);
  }, [groupedTickets, filters]);

  const filteredOrphans = useMemo(() => {
      return orphans.filter(filterTicket);
  }, [orphans, filters]);


  const getTicketTitle = (id) => {
    if (!id) return 'Unknown';
    const idStr = normalizeId(id);
    if (!idStr) return 'Unknown';
    const t = tickets.find(ticket => {
      const ticketId = normalizeId(ticket.id || ticket._id);
      return ticketId === idStr;
    });
    return t ? t.title : `...${idStr.slice(-6)}`;
  };

  const getTicketById = (id) => {
    if (!id) return null;
    const idStr = normalizeId(id);
    if (!idStr) return null;
    return tickets.find(ticket => {
      const ticketId = normalizeId(ticket.id || ticket._id);
      return ticketId === idStr;
    });
  };

  const getStatusColor = (status) => {
    switch (status?.toLowerCase()) {
      case 'todo': return 'bg-gray-400';
      case 'in_progress': return 'bg-yellow-400';
      case 'done': return 'bg-green-500';
      default: return 'bg-red-400';
    }
  };

  return (
    <div className="min-h-screen bg-gray-100 p-8 font-sans text-gray-900">
      <div className="max-w-7xl mx-auto">
        <header className="mb-8 flex justify-between items-center">
          <div>
            <h1 className="text-3xl font-bold text-gray-800">Project Engine Debugger</h1>
            <p className="text-gray-600">Tickets & File Browser</p>
          </div>
          <div className="flex gap-2">
            {activeTab === 'tickets' && (
              <button
                onClick={fetchTickets}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded shadow transition"
              >
                Refresh Tickets
              </button>
            )}
            {activeTab === 'files' && (
              <button
                onClick={fetchFileStructure}
                className="bg-blue-600 hover:bg-blue-700 text-white px-4 py-2 rounded shadow transition"
                disabled={fileLoading}
              >
                {fileLoading ? 'Loading...' : 'Refresh Files'}
              </button>
            )}
          </div>
        </header>

        {/* Tabs */}
        <div className="mb-6 flex gap-2 border-b border-gray-300">
          <button
            onClick={() => setActiveTab('tickets')}
            className={`px-4 py-2 font-semibold transition ${
              activeTab === 'tickets'
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            Tickets
          </button>
          <button
            onClick={() => setActiveTab('files')}
            className={`px-4 py-2 font-semibold transition ${
              activeTab === 'files'
                ? 'border-b-2 border-blue-600 text-blue-600'
                : 'text-gray-500 hover:text-gray-700'
            }`}
          >
            File Browser
          </button>
        </div>

        {/* Content */}
        {activeTab === 'tickets' ? (
          <>
            {loading ? (
              <div className="text-center py-10 text-gray-500">Loading tickets...</div>
            ) : error ? (
              <div className="text-center py-10 text-red-500">Error: {error}</div>
            ) : (
              <div className="space-y-6">
                {/* Filters */}
                <div className="bg-white p-4 rounded-lg shadow flex flex-wrap gap-4 items-center">
                  <FilterSelect 
                     label="Status" 
                     value={filters.status} 
                     onChange={(e) => setFilters(prev => ({ ...prev, status: e.target.value }))}
                     options={[
                       { value: 'all', label: 'All Statuses' },
                       { value: 'todo', label: 'Todo' },
                       { value: 'in_progress', label: 'In Progress' },
                       { value: 'done', label: 'Done' },
                     ]}
                   />
                   <div className="flex flex-col">
                     <label className="text-xs font-semibold text-gray-500 uppercase mb-1">Assigned To</label>
                     <select 
                        value={filters.assignee} 
                        onChange={(e) => setFilters(prev => ({ ...prev, assignee: e.target.value }))}
                        className="border border-gray-300 rounded p-2 min-w-[150px] focus:ring-2 focus:ring-blue-500 outline-none"
                     >
                        <option value="all">All Users</option>
                        {assignees.map(a => <option key={a} value={a}>{a}</option>)}
                     </select>
                   </div>
                   
                   <div className="flex-grow text-right text-gray-500 text-sm">
                       Epics: {filteredGroups.length} | Orphans: {filteredOrphans.length}
                   </div>
                </div>

                {/* Epics List */}
                {filteredGroups.map(epic => (
                    <EpicAccordion 
                        key={epic.id || epic._id} 
                        epic={epic} 
                        getTicketTitle={getTicketTitle}
                        getStatusColor={getStatusColor}
                        getTicketById={getTicketById}
                    />
                ))}

                {/* Orphans */}
                {filteredOrphans.length > 0 && (
                    <div className="mt-8 pt-8 border-t-2 border-gray-200">
                        <h2 className="text-xl font-bold text-gray-700 mb-4">Orphan Stories (No Epic)</h2>
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                            {filteredOrphans.map(t => (
                                <TicketCard 
                                    key={t.id || t._id} 
                                    ticket={t} 
                                    getTicketTitle={getTicketTitle} 
                                    getStatusColor={getStatusColor}
                                    getTicketById={getTicketById}
                                />
                            ))}
                        </div>
                    </div>
                )}
                
                {filteredGroups.length === 0 && filteredOrphans.length === 0 && (
                     <div className="text-center py-10 text-gray-500">No tickets found matching filters.</div>
                )}
              </div>
            )}
          </>
        ) : (
          <FileBrowser 
            fileStructure={fileStructure}
            fileContent={fileContent}
            selectedFile={selectedFile}
            fileLoading={fileLoading}
            fileError={fileError}
            onFileSelect={fetchFileContent}
            onRefresh={fetchFileStructure}
          />
        )}
      </div>
    </div>
  );
}

const EpicAccordion = ({ epic, getTicketTitle, getStatusColor, getTicketById }) => {
    const [isOpen, setIsOpen] = useState(true); // Default open

    return (
        <div className="bg-white rounded-lg shadow overflow-hidden border border-gray-200">
            <div 
                className="bg-gray-50 p-4 flex justify-between items-center cursor-pointer hover:bg-gray-100 transition"
                onClick={() => setIsOpen(!isOpen)}
            >
                <div className="flex items-center gap-4">
                    <button className="text-gray-500 focus:outline-none">
                        <svg className={`w-5 h-5 transform transition-transform ${isOpen ? 'rotate-180' : ''}`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M19 9l-7 7-7-7" />
                        </svg>
                    </button>
                    <div className="flex flex-col">
                        <div className="flex items-center gap-2">
                            <span className="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide bg-purple-100 text-purple-800">
                                EPIC
                            </span>
                            <h3 className="text-lg font-bold text-gray-900">{epic.title}</h3>
                        </div>
                         <p className="text-sm text-gray-500 mt-1 line-clamp-1">{epic.description || 'No description'}</p>
                    </div>
                </div>
                <div className="flex items-center gap-4">
                     <span className={`inline-block w-3 h-3 rounded-full ${getStatusColor(epic.status)}`}></span>
                     <span className="text-sm text-gray-500 font-mono" title={epic.id || epic._id}>...{String(epic.id || epic._id).slice(-6)}</span>
                </div>
            </div>
            
            {isOpen && (
                <div className="p-4 bg-gray-50/50 border-t border-gray-100">
                    {epic.children && epic.children.length > 0 ? (
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
                            {epic.children.map(story => (
                                <TicketCard 
                                    key={story.id || story._id} 
                                    ticket={story} 
                                    getTicketTitle={getTicketTitle} 
                                    getStatusColor={getStatusColor}
                                    getTicketById={getTicketById}
                                    isChild={true}
                                />
                            ))}
                        </div>
                    ) : (
                        <div className="text-sm text-gray-400 italic text-center py-2">No stories linked to this epic.</div>
                    )}
                </div>
            )}
        </div>
    );
};

const FilterSelect = ({ label, value, onChange, options }) => (
  <div className="flex flex-col">
    <label className="text-xs font-semibold text-gray-500 uppercase mb-1">{label}</label>
    <select 
      value={value} 
      onChange={onChange} 
      className="border border-gray-300 rounded p-2 min-w-[150px] focus:ring-2 focus:ring-blue-500 outline-none"
    >
      {options.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  </div>
);

const TicketCard = ({ ticket, getTicketTitle, getStatusColor, getTicketById, isChild = false }) => {
  const isEpic = ticket.type === 'epic';
  // If it's a child view, we style it slightly differently to fit better
  const typeColor = isEpic ? 'bg-purple-100 text-purple-800' : 'bg-blue-100 text-blue-800';
  const date = ticket.created_at ? new Date(ticket.created_at).toLocaleDateString() : 'Unknown Date';
  const idDisplay = String(ticket.id || ticket._id).slice(-6);
  
  // Get dependency names
  const dependencies = ticket.dependencies || [];
  const dependencyTitles = dependencies
    .map(depId => {
      const depTicket = getTicketById(depId);
      return depTicket ? depTicket.title : null;
    })
    .filter(Boolean);

  return (
    <div className={`bg-white rounded border ${isChild ? 'shadow-sm border-gray-200' : 'shadow border-l-4 ' + (isEpic ? 'border-purple-500' : 'border-blue-500')} p-4 flex flex-col h-full hover:shadow-md transition-shadow duration-200`}>
      <div className="flex justify-between items-start mb-2">
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wide ${typeColor}`}>
          {ticket.type || 'Unknown'}
        </span>
        <span className="text-xs text-gray-400 font-mono" title={String(ticket.id || ticket._id)}>...{idDisplay}</span>
      </div>
      
      <h4 className="text-md font-bold text-gray-900 mb-1 leading-tight line-clamp-2">{ticket.title || 'Untitled'}</h4>
      
      <p className="text-gray-600 text-xs mb-3 flex-grow line-clamp-3">{ticket.description || 'No description provided.'}</p>
      
      {/* Dependencies */}
      {dependencyTitles.length > 0 && (
        <div className="mb-3 pt-2 border-t border-gray-100">
          <div className="text-xs font-semibold text-gray-500 mb-1">Depends on:</div>
          <div className="flex flex-wrap gap-1">
            {dependencyTitles.map((title, idx) => (
              <span key={idx} className="px-2 py-0.5 bg-yellow-50 text-yellow-700 rounded text-[10px] border border-yellow-200">
                {title}
              </span>
            ))}
          </div>
        </div>
      )}
      
      <div className="flex items-center justify-between mt-auto pt-2 border-t border-gray-50">
          <div className="flex items-center gap-2 text-xs text-gray-500">
             <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2" d="M16 7a4 4 0 11-8 0 4 4 0 018 0zM12 14a7 7 0 00-7 7h14a7 7 0 00-7-7z"></path></svg>
             <span className="max-w-[100px] truncate">{ticket.assigned_to || 'Unassigned'}</span>
          </div>
          <span className={`inline-block w-2 h-2 rounded-full ${getStatusColor(ticket.status)}`} title={ticket.status}></span>
      </div>
    </div>
  );
};

const FileBrowser = ({ fileStructure, fileContent, selectedFile, fileLoading, fileError, onFileSelect, onRefresh }) => {
  const [expandedPaths, setExpandedPaths] = useState(new Set(['/app']));

  const toggleExpand = (path) => {
    const newExpanded = new Set(expandedPaths);
    if (newExpanded.has(path)) {
      newExpanded.delete(path);
    } else {
      newExpanded.add(path);
    }
    setExpandedPaths(newExpanded);
  };

  const renderFileTree = (items, level = 0, parentPath = '/app') => {
    if (!items || !Array.isArray(items) || items.length === 0) return null;

    return (
      <div className={`${level > 0 ? 'ml-4' : ''}`}>
        {items.map((item, idx) => {
          // Construct full path for this item
          const fullPath = item.path || (parentPath === '/app' ? `/app/${item.name}` : `${parentPath}/${item.name}`);
          const uniqueKey = `${parentPath}-${item.name}-${idx}`;
          
          return (
            <div key={uniqueKey}>
              <div 
                className={`flex items-center py-1 px-2 hover:bg-gray-50 cursor-pointer rounded ${
                  selectedFile === item.path ? 'bg-blue-50 border-l-2 border-blue-500' : ''
                }`}
                onClick={() => {
                  if (item.type === 'file') {
                    onFileSelect(item.path);
                  } else {
                    toggleExpand(fullPath);
                  }
                }}
              >
                <span className="mr-2 text-gray-400">
                  {item.type === 'file' ? '📄' : expandedPaths.has(fullPath) ? '📂' : '📁'}
                </span>
                <span className="text-sm text-gray-700">{item.name}</span>
                {item.type === 'file' && (
                  <span className="ml-auto text-xs text-gray-400">{item.path}</span>
                )}
              </div>
              {item.type === 'dir' && expandedPaths.has(fullPath) && item.children && (
                <div className="ml-2">
                  {renderFileTree(item.children, level + 1, fullPath)}
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  };

  return (
    <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
      {/* File Tree */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold text-gray-800">File Structure</h2>
          <button
            onClick={onRefresh}
            disabled={fileLoading}
            className="text-sm text-blue-600 hover:text-blue-700 disabled:text-gray-400"
          >
            {fileLoading ? 'Loading...' : 'Refresh'}
          </button>
        </div>
        
        {fileError ? (
          <div className="text-red-500 text-sm py-4">
            {fileError}
          </div>
        ) : fileLoading && !fileStructure ? (
          <div className="text-gray-500 text-sm py-4">Loading file structure...</div>
        ) : fileStructure ? (
          <div className="max-h-[600px] overflow-y-auto">
            {renderFileTree(fileStructure)}
          </div>
        ) : (
          <div className="text-gray-500 text-sm py-4">No files found. Make sure the container is running.</div>
        )}
      </div>

      {/* File Content */}
      <div className="bg-white rounded-lg shadow p-4">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold text-gray-800">File Content</h2>
          {selectedFile && (
            <span className="text-xs text-gray-500 font-mono">{selectedFile}</span>
          )}
        </div>
        
        {fileLoading && selectedFile ? (
          <div className="text-gray-500 text-sm py-4">Loading file content...</div>
        ) : fileError && selectedFile ? (
          <div className="text-red-500 text-sm py-4">{fileError}</div>
        ) : fileContent ? (
          <div className="max-h-[600px] overflow-auto">
            <pre className="text-xs bg-gray-50 p-4 rounded border border-gray-200 whitespace-pre-wrap break-words">
              {fileContent.content}
            </pre>
            <div className="mt-2 text-xs text-gray-500">
              Size: {fileContent.size} characters
            </div>
          </div>
        ) : (
          <div className="text-gray-500 text-sm py-4">Select a file to view its content</div>
        )}
      </div>
    </div>
  );
};

export default App;
