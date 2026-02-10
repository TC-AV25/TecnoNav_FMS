import routes from '../routes/sidebar'
import { NavLink, Link , useLocation} from 'react-router-dom'
import SidebarSubmenu from './SidebarSubmenu';
import XMarkIcon  from '@heroicons/react/24/outline/XMarkIcon'
import ChevronLeftIcon from '@heroicons/react/24/outline/ChevronLeftIcon'
import ChevronRightIcon from '@heroicons/react/24/outline/ChevronRightIcon'
import { useState } from 'react';

function LeftSidebar(){
    const location = useLocation();
    const [isCollapsed, setIsCollapsed] = useState(false);


    const close = (e) => {
        document.getElementById('left-sidebar-drawer').click()
    }

    const toggleCollapse = () => {
        setIsCollapsed(!isCollapsed)
    }

    return(
        <div className="drawer-side ">
            <label htmlFor="left-sidebar-drawer" className="drawer-overlay"></label> 
            <div className={`flex flex-col h-full bg-base-100 text-base-content transition-all duration-300 ${isCollapsed ? 'w-20' : 'w-80'}`}>
                <div className="flex items-center justify-between pt-2 px-2">
                    <button className="btn btn-ghost bg-base-300 btn-circle z-50 lg:hidden" onClick={() => close()}>
                        <XMarkIcon className="h-5 inline-block w-5"/>
                    </button>
                    <button className="btn btn-ghost btn-circle hidden lg:flex ml-auto" onClick={toggleCollapse} title={isCollapsed ? "Expand sidebar" : "Collapse sidebar"}>
                        {isCollapsed ? <ChevronRightIcon className="h-5 w-5" /> : <ChevronLeftIcon className="h-5 w-5" />}
                    </button>
                </div>
                
                {/* Logo */}
                <div className={`${isCollapsed ? 'px-2' : 'px-4'} py-4 flex items-center justify-center`}>
                    <img src="/TecnoNav_logo_noback.png" alt="TecnoNav Logo" className={`${isCollapsed ? 'w-16 h-16' : 'w-32 h-32'} object-contain transition-all duration-300`} />
                </div>

                <ul className="menu pt-2 px-0 flex-1 overflow-y-auto">
                    <li className={`mb-2 font-semibold ${isCollapsed ? 'px-2' : 'px-4'}`}>
                        <Link to={'/app/welcome'} title={isCollapsed ? "TECNONAV DASHBOARD" : ""} className={isCollapsed ? 'justify-center' : ''}>
                            {!isCollapsed && <span className="text-xl">TECNONAV DASHBOARD</span>}
                            {isCollapsed && <span className="text-lg">TD</span>}
                        </Link>
                    </li>
                    {
                        routes.map((route, k) => {
                            return(
                                <li className={isCollapsed ? 'px-2' : ''} key={k}>
                                    {
                                        route.submenu ? 
                                            <SidebarSubmenu {...route} isCollapsed={isCollapsed}/> : 
                                        (<NavLink
                                            end
                                            to={route.path}
                                            title={isCollapsed ? route.name : ""}
                                            className={({isActive}) => `${isActive ? 'font-semibold  bg-base-200 ' : 'font-normal'} ${isCollapsed ? 'justify-center' : ''}`} >
                                               {route.icon} {!isCollapsed && <span>{route.name}</span>}
                                                {
                                                    location.pathname === route.path ? (<span className={`absolute inset-y-0 ${isCollapsed ? '-left-2' : 'left-0'} w-1 rounded-tr-md rounded-br-md bg-primary `}
                                                    aria-hidden="true"></span>) : null
                                                }
                                        </NavLink>)
                                    }
                                    
                                </li>
                            )
                        })
                    }

                </ul>
            </div>
        </div>
    )
}

export default LeftSidebar